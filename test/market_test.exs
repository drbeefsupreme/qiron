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
    call.({:hold, true})
    stop_supervised!(Market)
    pid = start_supervised!({Market, opts})
    assert :liquidated = Market.call({:refill, "a"}, pid)
    assert %{held: true, mark: 400.0, layers: layers} = Market.call(:stage, pid)
    assert Enum.at(layers, 3).text == "CAW"
    assert %{side: "flat", piss_coin: 45_000.0} = Market.call({:account, "b"}, pid)
    assert :ok = Market.call({:line, 4, ""}, pid)
    assert Enum.at(Market.call(:stage, pid).layers, 3).text == "BLOOD"
  end

  @tag :tmp_dir
  test "a saved seat can claim one slug after its five-minute wait", %{tmp_dir: dir} do
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
    assert %{refill_in: 0} = Market.call({:account, "a"}, pid)
    assert :liquidated = Market.call({:trade, "a", "up", 50}, pid)
    assert %{piss_coin: 50_000.0, refill_in: nil} = Market.call({:refill, "a"}, pid)
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
end
