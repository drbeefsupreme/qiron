defmodule Qiron.PnlHistoryTest do
  use ExUnit.Case, async: true
  alias Qiron.Market

  @tag :tmp_dir
  test "marks and settled trades accumulate P&L without polling, and one liquidation closes the run",
       %{tmp_dir: dir} do
    opts = [path: Path.join(dir, "show"), tick: false]
    pid = start_supervised!({Market, opts})
    call = &Market.call(&1, pid)

    assert %{pnl_runs: [%{id: 1, started_at_ms: start, points: [[at, 0]]}]} =
             call.({:account, "seat"})

    assert start == at
    assert %{pnl_runs: [%{id: 1}]} = call.({:trade, "seat", "up", 2})
    call.({:mark, 11_000})
    call.({:mark, 10_500})
    assert %{piss_coin: 55_000.0} = call.({:trade, "seat", "flat", 1})
    call.({:mark, 20_000})
    call.({:trade, "seat", "down", 50})
    call.({:mark, 20_400})
    call.({:mark, 21_000})
    result = call.({:account, "seat"})
    assert [%{id: 1, ended_at_ms: ended, points: points}] = result.pnl_runs
    assert [^ended, -5_000_000] = List.last(points)
    assert ended <= result.as_of_ms
    assert Enum.sort_by(points, &hd/1) == points
    assert Enum.dedup(Enum.map(points, &List.last/1)) == [0, 1_000_000, 500_000, -5_000_000]
    assert :liquidated = call.({:refill, "seat"})
    assert :liquidated = call.({:trade, "seat", "up", 1})
    assert %{pnl_runs: [%{id: 1, points: [[_, 0]]}]} = call.({:account, "another"})
    stop_supervised!(Market)
    pid = start_supervised!({Market, opts})
    assert Market.call({:account, "seat"}, pid).pnl_runs == result.pnl_runs
  end

  @tag :tmp_dir
  test "the market tick grants the next slug at its deadline with no phone open", %{tmp_dir: dir} do
    path = Path.join(dir, "show")
    now = System.system_time(:millisecond)
    deadline = now + 400
    bust = deadline - 300_000
    seat = %{side: "flat", bank: 0, entry: 10_000, leverage: 1, refill_at: deadline}
    File.write!(path, :erlang.term_to_binary(%Market{players: %{"seat" => seat}, held: true}))
    pid = start_supervised!({Market, path: path, tick: false})
    Process.sleep(max(0, deadline - System.system_time(:millisecond) + 1))
    send(pid, :tick)
    Market.call(:stage, pid)
    saved = File.read!(path) |> :erlang.binary_to_term()
    assert saved.players["seat"].bank == 5_000_000
    assert saved.players["seat"].refill_at == nil

    assert %{
             pnl_runs: [
               %{id: 1, ended_at_ms: ^bust, points: [[^bust, -5_000_000]]},
               %{id: 2, started_at_ms: ^deadline, points: [[^deadline, 0]], ended_at_ms: nil}
             ]
           } = Market.call({:account, "seat"}, pid)

    assert :invalid = Market.call({:refill, "seat"}, pid)
    Market.call({:trade, "seat", "down", 3}, pid)
    Market.call({:mark, 9_900}, pid)
    assert %{pnl_runs: [_, %{points: points}]} = Market.call({:account, "seat"}, pid)
    assert List.last(points) |> List.last() == 150_000
  end

  @tag :tmp_dir
  test "old active accounts begin at observed equity and long histories retain their endpoints and extrema",
       %{tmp_dir: dir} do
    path = Path.join(dir, "show")
    seat = %{side: "up", bank: 5_000_000, entry: 9000, leverage: 1, refill_at: nil}
    File.write!(path, :erlang.term_to_binary(%Market{players: %{"seat" => seat}}))
    pid = start_supervised!({Market, path: path, tick: false})
    call = &Market.call(&1, pid)
    assert %{pnl_runs: [%{points: [first]}]} = call.({:account, "seat"})
    assert List.last(first) == 555_556
    call.({:mark, 90_000})
    for mark <- 10_001..10_500, do: call.({:mark, mark})
    assert %{pnl_runs: [%{points: points}]} = call.({:account, "seat"})
    assert length(points) <= 192
    assert hd(points) == first
    assert points |> Enum.map(&List.last/1) |> Enum.max() == 45_000_000
    assert List.last(points) |> List.last() == 833_333
  end
end
