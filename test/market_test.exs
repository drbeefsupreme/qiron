defmodule Qiron.MarketTest do
  use ExUnit.Case, async: true
  alias Qiron.Market

  @tag :tmp_dir
  test "two seats settle against one mark and recover after a restart", %{tmp_dir: dir} do
    opts = [path: Path.join(dir, "show"), tick: false]
    pid = start_supervised!({Market, opts})
    call = &Market.call(&1, pid)
    call.({:trade, "a", "up"})
    call.({:trade, "b", "down"})
    call.({:mark, 11_000})
    assert %{up: 1, down: 1} = call.(:stage)
    assert %{credits: 1010.0} = call.({:trade, "a", "up"})
    assert %{credits: 990.0} = call.({:trade, "b", "flat"})
    call.({:trade, "a", "down"})
    call.({:mark, 40_000})
    assert %{side: "flat", credits: 910.0} = call.({:account, "a"})
    call.({:line, 4, "CAW"})
    call.({:hold, true})
    stop_supervised!(Market)
    pid = start_supervised!({Market, opts})
    assert %{held: true, mark: 400.0, layers: layers} = Market.call(:stage, pid)
    assert Enum.at(layers, 3).text == "CAW"
    assert %{side: "flat", credits: 990.0} = Market.call({:account, "b"}, pid)
    assert :ok = Market.call({:line, 4, ""}, pid)
    assert Enum.at(Market.call(:stage, pid).layers, 3).text == "BLOOD"
  end
end
