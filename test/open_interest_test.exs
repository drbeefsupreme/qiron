defmodule Qiron.OpenInterestTest do
  use ExUnit.Case, async: true
  alias Qiron.Market

  @tag :tmp_dir
  test "open interest follows position size and mark, and excludes closed and liquidated seats",
       %{tmp_dir: dir} do
    pid = start_supervised!({Market, path: Path.join(dir, "show"), tick: false})
    call = &Market.call(&1, pid)
    assert %{long_oi_cents: 0, short_oi_cents: 0} = call.(:stage)
    call.({:trade, "one", "up", 2})
    call.({:trade, "two", "down", 3})
    assert %{long_oi_cents: 10_000_000, short_oi_cents: 15_000_000} = call.(:panel)
    call.({:mark, 11_000})
    assert %{long_oi_cents: 11_000_000, short_oi_cents: 16_500_000} = call.(:stage)
    call.({:trade, "one", "flat", 1})
    assert %{long_oi_cents: 0, short_oi_cents: 16_500_000} = call.(:stage)
    call.({:mark, 13_334})
    assert %{long_oi_cents: 0, short_oi_cents: 0} = call.(:stage)
    assert %{side: "flat", piss_coin: +0.0} = call.({:account, "two"})
  end

  @tag :tmp_dir
  test "each position rounds to cents before summation", %{tmp_dir: dir} do
    path = Path.join(dir, "show")
    p = %{bank: 1, leverage: 1, entry: 200, side: "up", refill_at: nil}
    File.write!(path, :erlang.term_to_binary(%Market{mark: 300, players: %{"a" => p, "b" => p}}))
    pid = start_supervised!({Market, path: path, tick: false})
    assert Market.call(:stage, pid).long_oi_cents == 4
    Market.call({:mark, 299}, pid)
    assert Market.call(:panel, pid).long_oi_cents == 2
  end

  @tag :tmp_dir
  test "the original Blood Futures stack upgrades once while authored stacks retain their widgets",
       %{tmp_dir: dir} do
    path = Path.join(dir, "show")
    opts = [path: path, tick: false]
    pid = start_supervised!({Market, opts})
    call = &Market.call(&1, pid)
    assert :ok = call.({:mode, "blood"})
    assert :ok = call.({:widgets, ["chart", "ticker"]})
    assert :ok = call.({:take, call.(:panel).revision})
    assert :ok = call.({:save_as, "As aired"})
    custom = call.(:panel).preset_id
    stop_supervised!(Market)
    show = File.read!(path) |> :erlang.binary_to_term() |> Map.delete(:blood_layout_version)
    File.write!(path, :erlang.term_to_binary(show))
    pid = start_supervised!({Market, opts})
    call = &Market.call(&1, pid)
    assert %{preset_id: ^custom, widgets: ["chart", "ticker"]} = call.(:panel)
    assert %{preset_id: "blood", widgets: ["chart", "price", "interest"]} = call.(:stage)
    assert :ok = call.({:mode, "blood"})
    assert call.(:panel).widgets == ~w(chart price interest)
    assert :ok = call.({:widgets, ["chart", "ticker"]})
    stop_supervised!(Market)
    pid = start_supervised!({Market, opts})
    assert Market.call(:panel, pid).widgets == ["chart", "ticker"]
  end
end
