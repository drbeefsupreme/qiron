defmodule Qiron.MarketTest do
  use ExUnit.Case, async: true
  alias Qiron.Market

  @tag :tmp_dir
  test "two seats settle against one mark and recover after a restart", %{tmp_dir: dir} do
    opts = [path: Path.join(dir, "show"), tick: false]
    pid = start_supervised!({Market, opts})
    call = &Market.call(&1, pid)
    call.({:trade, "a", "up", 5})
    call.({:trade, "b", "down", 1})
    call.({:mark, 11_000})
    assert %{up: 1, down: 1} = call.(:stage)
    assert %{piss_coin: 75_000.0} = call.({:trade, "a", "up", 5})
    assert %{piss_coin: 45_000.0} = call.({:trade, "b", "flat", 1})
    call.({:trade, "a", "down", 50})
    call.({:mark, 40_000})
    assert %{side: "flat", piss_coin: +0.0} = call.({:account, "a"})
    assert %{refill_in: wait} = call.({:account, "a"})
    assert wait in 299..300
    assert :liquidated = call.({:trade, "a", "up", 1})
    assert :liquidated = call.({:refill, "a"})
    call.({:line, 4, "CAW"})
    call.({:take, call.(:panel).revision})
    call.({:hold, true})
    stop_supervised!(Market)
    pid = start_supervised!({Market, opts})
    assert :liquidated = Market.call({:refill, "a"}, pid)
    assert %{held: true, mark: 400.0, layers: layers} = Market.call(:stage, pid)
    assert Enum.at(layers, 3).text == "CAW"
    assert %{side: "flat", piss_coin: 45_000.0} = Market.call({:account, "b"}, pid)
    assert :ok = Market.call({:line, 4, ""}, pid)
    assert Enum.at(Market.call(:panel, pid).layers, 3).text == ""
    assert Enum.at(Market.call(:stage, pid).layers, 3).text == "CAW"
  end

  @tag :tmp_dir
  test "quoted liquidation matches settlement, side switches, and limits", %{tmp_dir: dir} do
    pid = start_supervised!({Market, path: Path.join(dir, "show"), tick: false})
    call = &Market.call(&1, pid)
    flat = call.({:account, "seat"})
    assert flat.liquidation_cents == nil
    assert flat.entry_cents == nil
    assert flat.mark_cents == 10_000
    assert Enum.at(flat.quotes_cents["up"], 0) == nil
    assert Enum.at(flat.quotes_cents["up"], 2) == 6666
    assert Enum.at(flat.quotes_cents["down"], 2) == 13_334
    assert %{liquidation_cents: 6666, entry_cents: 10_000} = call.({:trade, "seat", "up", 3})

    call.({:mark, 6667})
    before_switch = call.({:account, "seat"})
    assert before_switch.side == "up"
    assert Enum.uniq(before_switch.quotes_cents["up"]) == [6666]
    next_trigger = Enum.at(before_switch.quotes_cents["down"], 49)
    assert %{liquidation_cents: ^next_trigger} = call.({:trade, "seat", "down", 50})
    call.({:mark, next_trigger - 1})
    assert call.({:account, "seat"}).side == "down"
    call.({:mark, next_trigger})
    assert %{side: "flat", quotes_cents: %{"up" => [], "down" => []}} = call.({:account, "seat"})

    call.({:mark, 1_000_000})
    assert Enum.uniq(call.({:account, "new"}).quotes_cents["down"]) == [nil]
  end

  @tag :tmp_dir
  test "liquidation quote reflects cent rounding on a nearly exhausted seat", %{tmp_dir: dir} do
    path = Path.join(dir, "show")
    seat = %{side: "flat", bank: 1, entry: 10_000, leverage: 1, refill_at: nil}
    File.write!(path, :erlang.term_to_binary(%Market{players: %{"seat" => seat}}))
    pid = start_supervised!({Market, path: path, tick: false})
    call = &Market.call(&1, pid)
    assert Enum.at(call.({:account, "seat"}).quotes_cents["up"], 49) == 9900
    assert %{liquidation_cents: 9900} = call.({:trade, "seat", "up", 50})
    call.({:mark, 9901})
    assert %{side: "up", piss_coin: 0.01} = call.({:account, "seat"})
    call.({:mark, 9900})
    assert %{side: "flat", piss_coin: +0.0} = call.({:account, "seat"})
  end

  @tag :tmp_dir
  test "a saved seat automatically gets one slug after its five-minute wait", %{tmp_dir: dir} do
    path = Path.join(dir, "show")

    seat = %{
      side: "flat",
      bank: 0,
      entry: 10000,
      leverage: 1,
      refill_at: System.system_time(:millisecond) - 1
    }

    File.write!(path, :erlang.term_to_binary(%Market{players: %{"a" => seat}}))
    pid = start_supervised!({Market, path: path, tick: false})
    assert %{piss_coin: 50_000.0, refill_in: nil} = Market.call({:account, "a"}, pid)
    assert :invalid = Market.call({:refill, "a"}, pid)

    for bad <- [0, 51, 1.5, "50", nil],
        do: assert(:invalid == Market.call({:trade, "a", "up", bad}, pid))

    assert %{side: "up", leverage: 50} = Market.call({:trade, "a", "up", 50}, pid)
    Market.call({:mark, 9800}, pid)
    assert %{side: "flat", piss_coin: +0.0} = Market.call({:account, "a"}, pid)
  end

  @tag :tmp_dir
  test "old positions settle once at the saved mark", %{tmp_dir: dir} do
    path = Path.join(dir, "show")
    seat = %{side: "up", bank: 100_000, entry: 10_000}
    File.write!(path, :erlang.term_to_binary(%Market{mark: 11_000, players: %{"a" => seat}}))

    for _ <- 1..2 do
      pid = start_supervised!({Market, path: path, tick: false})
      assert %{side: "flat", piss_coin: 50_500.0} = Market.call({:account, "a"}, pid)
      stop_supervised!(Market)
    end
  end

  @tag :tmp_dir
  test "upgrade restores old overlays; prepared scenes and candle data survive a restart", %{
    tmp_dir: dir
  } do
    path = Path.join(dir, "show")

    old = %{
      __struct__: Market,
      mark: 12000,
      held: true,
      previous: 12000,
      players: %{},
      brightness: 64,
      speeds: %{4 => 7},
      lines: %{4 => "CAW"}
    }

    File.write!(path, :erlang.term_to_binary(old))
    opts = [path: path, tick: false]
    pid = start_supervised!({Market, opts})
    call = &Market.call(&1, pid)

    assert %{mode: "gif", brightness: 64, layers: layers, dirty: false, revision: 0} =
             call.(:panel)

    assert %{text: "CAW", speed: 7} = Enum.at(layers, 3)
    assert :invalid = call.({:gif, "gifJ", "/gifs/joker/../private.gif"})
    assert :invalid = call.({:gif, "gifJ", "/gifs/flag/test.gif"})
    assert :ok = call.({:gif, "gifJ", "/gifs/joker/telethon.gif"})
    assert :ok = call.({:action, "hitShapes"})
    assert :ok = call.({:take, 2})
    assert %{gif: %{file: "/gifs/joker/telethon.gif"}, mode: "gif"} = call.(:stage)
    assert %{action: nil, dirty: false} = call.(:panel)
    assert :ok = call.({:mode, "intro"})
    assert :wrong_mode = call.({:action, "hitShapes"})
    assert :wrong_mode = call.({:line, 2, "later"})
    assert :ok = call.({:brightness, 127})
    assert :ok = call.({:mark, 13000})
    assert :ok = call.({:mark, 11500})
    assert :ok = call.({:mark, 12800})
    assert %{mode: "gif", candles: bars, mark: 128.0} = call.(:stage)
    assert List.first(bars).open == 12000
    assert Enum.max_by(bars, & &1.high).high == 13000
    assert Enum.min_by(bars, & &1.low).low == 11500
    assert List.last(bars).close == 12800
    assert :stale = call.({:take, 0})
    stop_supervised!(Market)
    pid = start_supervised!({Market, opts})
    call = &Market.call(&1, pid)

    assert %{mode: "intro", live_mode: "gif", dirty: true, revision: 5, brightness: 127} =
             call.(:panel)

    assert :ok = call.({:take, 5})
    assert %{mode: "intro"} = call.(:stage)
    assert :ok = call.({:mode, "blood"})
    call.({:trade, "viewer", "down", 5})
    assert :ok = call.({:take, 7})
    assert %{mode: "blood", down: 1, candles: candles} = call.(:stage)
    assert List.last(candles).close == 12800
    assert :ok = call.({:mode, "gif"})
    assert %{gif: %{file: "/gifs/joker/telethon.gif"}, layers: layers} = call.(:panel)
    assert Enum.at(layers, 3).text == "CAW"
  end

  @tag :tmp_dir
  test "old candles age out without backfilling missing observations", %{tmp_dir: dir} do
    path = Path.join(dir, "show")
    bucket = div(System.system_time(:second), 10) * 10

    bars =
      for ago <- [20, 240, 250],
          do: %{bucket: bucket - ago, open: 100, high: 100, low: 100, close: 100}

    File.write!(path, :erlang.term_to_binary(%Market{candles: bars}))
    pid = start_supervised!({Market, path: path, tick: false})
    assert %{candles: [earlier, current]} = Market.call(:stage, pid)
    assert earlier.bucket == bucket - 20
    assert current.bucket >= bucket
    assert current.close == 10000
  end
end
