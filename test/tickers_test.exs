defmodule Qiron.TickersTest do
  use ExUnit.Case, async: true
  alias Qiron.Market

  @tag :tmp_dir
  test "ticker quotes move independently of a held oracle and survive restart", %{tmp_dir: dir} do
    path = Path.join(dir, "show")
    old = Map.delete(%Market{held: true}, :ticker_prices)
    File.write!(path, :erlang.term_to_binary(old))
    opts = [path: path, tick: false]
    pid = start_supervised!({Market, opts})
    initial = Market.call(:stage, pid)

    assert Enum.map(initial.tickers, & &1.symbol) == [
             "PISSCOIN",
             "PRICECOIN",
             "BONER",
             "FARTCOIN",
             "ROGUE",
             "CROW"
           ]

    assert Enum.map(initial.tickers, & &1.color) ==
             ~w(#FFD84A #54CFFF #FF77B7 #A9EC5C #C18EFF #FF9259)

    send(pid, :tick)
    next = Market.call(:stage, pid)
    assert next.mark == initial.mark

    assert Enum.zip(initial.tickers, next.tickers)
           |> Enum.all?(fn {a, b} ->
             a.price_cents != b.price_cents and b.price_cents > 0
           end)

    assert :invalid = Market.call({:trade, "seat", "CROW", 1}, pid)
    stop_supervised!(Market)
    pid = start_supervised!({Market, opts})
    assert Market.call(:stage, pid).tickers == next.tickers
  end
end
