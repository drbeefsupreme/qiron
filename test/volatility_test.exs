defmodule Qiron.VolatilityTest do
  use ExUnit.Case, async: true
  alias Qiron.Market

  @tag :tmp_dir
  test "live volatility restores across shows and respects drift hold", %{tmp_dir: dir} do
    path = Path.join(dir, "show")
    opts = [path: path, tick: false]
    old = Map.delete(%Market{}, :volatility_bps)
    File.write!(path, :erlang.term_to_binary(old))
    pid = start_supervised!({Market, opts})
    assert Market.call(:panel, pid).volatility_bps == 50
    assert :ok = Market.call({:volatility_bps, 0}, pid)
    send(pid, :tick)
    assert Market.call(:stage, pid).mark_cents == 10_000
    assert :ok = Market.call({:volatility_bps, 500}, pid)
    assert :ok = Market.call({:hold, true}, pid)
    send(pid, :tick)
    assert Market.call(:stage, pid).mark_cents == 10_000
    assert Market.call(:panel, pid).dirty == false
    assert :invalid = Market.call({:volatility_bps, 501}, pid)
    stop_supervised!(Market)
    pid = start_supervised!({Market, opts})
    assert %{held: true, volatility_bps: 500} = Market.call(:panel, pid)
    assert :ok = Market.call({:hold, false}, pid)
    send(pid, :tick)
    assert Market.call(:stage, pid).mark_cents in 9_500..10_500
  end
end
