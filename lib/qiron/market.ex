defmodule Qiron.Market do
  use GenServer
  alias Qiron.Display

  @min_mark 100
  @max_mark 1_000_000
  @slug 5_000_000
  @cooldown_ms 300_000
  @tickers [
    {"PISSCOIN", "#FFD84A", 1250},
    {"PRICECOIN", "#54CFFF", 2400},
    {"BONER", "#FF77B7", 6900},
    {"FARTCOIN", "#A9EC5C", 420},
    {"ROGUE", "#C18EFF", 8700},
    {"CROW", "#FF9259", 3300}
  ]

  defstruct mark: 10000,
            previous: 10000,
            held: false,
            volatility_bps: 50,
            players: %{},
            display: %Display{},
            draft: nil,
            revision: 0,
            pending_action: nil,
            candles: [],
            ticker_seed: nil,
            ticker_prices: Enum.map(@tickers, &elem(&1, 2))

  def start_link(opts), do: GenServer.start_link(__MODULE__, opts, Keyword.take(opts, [:name]))
  def call(command, server \\ __MODULE__), do: GenServer.call(server, command)

  def init(opts) do
    path = Keyword.fetch!(opts, :path)

    show =
      case File.read(path) do
        {:ok, bytes} -> :erlang.binary_to_term(bytes, [:safe])
        {:error, :enoent} -> %__MODULE__{}
      end

    if Keyword.get(opts, :tick, true), do: Process.send_after(self(), :tick, 2000)

    display =
      Map.get_lazy(show, :display, fn ->
        Map.take(show, [:lines, :speeds, :brightness])
      end)

    next =
      struct(__MODULE__, Map.delete(show, :__struct__))
      |> Map.put(:display, Display.restore(display))
      |> Map.put(:draft, Display.restore(Map.get(show, :draft) || display))

    {:ok, persist(next |> migrate_accounts() |> record_mark(), show, path)}
  end

  def handle_info(:tick, {s, path}) do
    next =
      if s.held do
        record_mark(s)
      else
        step = :rand.uniform(2 * s.volatility_bps + 1) - s.volatility_bps - 1
        move(s, div(s.mark * (10_000 + step) + 5_000, 10_000))
      end

    seed = if s.ticker_seed, do: :rand.seed_s(s.ticker_seed), else: :rand.seed_s(:exsss)
    {prices, seed} = Enum.map_reduce(s.ticker_prices, seed, &tick_price/2)
    next = %{next | ticker_prices: prices, ticker_seed: :rand.export_seed_s(seed)}
    Process.send_after(self(), :tick, 2000)
    {:noreply, persist(next, s, path)}
  end

  def handle_call(command, _, {s, path}) do
    {next, reply} = apply_command(command, s)
    {:reply, reply, persist(next, s, path)}
  end

  defp tick_price(price, seed) do
    {step, seed} = :rand.uniform_s(max(1, div(price, 50)), seed)
    {direction, seed} = :rand.uniform_s(2, seed)
    next = if direction == 1, do: max(1, price - step), else: min(@max_mark, price + step)
    {next, seed}
  end

  defp persist(s, s, path), do: {s, path}

  defp persist(next, _, path) do
    File.mkdir_p!(Path.dirname(path))
    File.write!(path <> ".tmp", :erlang.term_to_binary(next), [:sync])
    File.rename!(path <> ".tmp", path)
    {next, path}
  end

  defp apply_command(:stage, s), do: {s, stage(s)}
  defp apply_command({:account, id}, s), do: {s, account(s, id)}

  defp apply_command({:trade, id, side, leverage}, s)
       when side in ["up", "down", "flat"] and leverage in 1..50 do
    p = player(s, id)

    cond do
      p.refill_at != nil ->
        {s, :liquidated}

      p.side == side ->
        {s, account(s, id)}

      true ->
        next = %{
          p
          | side: side,
            entry: s.mark,
            bank: equity(p, s.mark),
            leverage: if(side == "flat", do: 1, else: leverage)
        }

        save_player(s, id, next)
    end
  end

  defp apply_command({:refill, id}, s) do
    case player(s, id).refill_at do
      nil ->
        {s, :invalid}

      deadline ->
        if System.system_time(:millisecond) >= deadline,
          do: save_player(s, id, fresh_player(s.mark)),
          else: {s, :liquidated}
    end
  end

  defp apply_command({:hold, held}, s) when is_boolean(held), do: {%{s | held: held}, :ok}

  defp apply_command({:volatility_bps, value}, s) when value in 0..500,
    do: {%{s | volatility_bps: value}, :ok}

  defp apply_command({:mark, cents}, s) when cents in @min_mark..@max_mark,
    do: {move(s, cents), :ok}

  defp apply_command({:nudge, dir}, s) when dir in [-1, 1],
    do: {move(s, round(s.mark * (1 + dir * 0.05))), :ok}

  defp apply_command(:panel, s) do
    draft = scene(s.draft, s)

    {s,
     Map.merge(draft, %{
       revision: s.revision,
       dirty: s.draft != s.display or s.pending_action != nil,
       live_mode: s.display.mode,
       live_melt: s.display.melt,
       live_hue: s.display.hue,
       action: s.pending_action
     })}
  end

  defp apply_command(:live_panel, s), do: {s, scene(s.display, s)}

  defp apply_command({:live_fx, melt, hue}, s) when melt in 0..100 and hue in 0..100 do
    display = %{s.display | melt: melt, hue: hue}

    draft =
      if s.draft == s.display and is_nil(s.pending_action),
        do: display,
        else: Display.remember_live_fx(s.draft, s.display, melt, hue)

    {%{s | display: display, draft: draft}, :ok}
  end

  defp apply_command({:take, rev}, %{revision: rev} = s) do
    {%{s | display: s.draft, pending_action: nil, revision: rev + 1}, :ok}
  end

  defp apply_command({:take, _}, s), do: {s, :stale}

  defp apply_command({:action, name}, s) do
    case Display.cue(s.draft, name) do
      {:ok, draft, action} -> edit(s, draft, action)
      error -> {s, error}
    end
  end

  defp apply_command(command, s) do
    case Display.change(s.draft, command) do
      {:ok, draft} ->
        action = if draft.mode == s.draft.mode and "sd" in draft.widgets, do: s.pending_action
        edit(s, draft, action)

      error ->
        {s, error}
    end
  end

  defp edit(%{draft: draft, pending_action: action} = s, draft, action), do: {s, :ok}

  defp edit(s, draft, action),
    do: {%{s | draft: draft, pending_action: action, revision: s.revision + 1}, :ok}

  defp record_mark(s) do
    bucket = div(System.system_time(:second), 10) * 10
    mark = s.mark

    candles =
      case s.candles do
        [%{bucket: ^bucket} = current | history] ->
          [
            %{current | high: max(current.high, mark), low: min(current.low, mark), close: mark}
            | history
          ]

        prior ->
          candle = %{bucket: bucket, open: mark, high: mark, low: mark, close: mark}
          [candle | Enum.filter(prior, &(&1.bucket < bucket and &1.bucket > bucket - 240))]
      end

    %{s | candles: candles}
  end

  defp move(s, cents) do
    mark = min(@max_mark, max(@min_mark, cents))

    deadline = System.system_time(:millisecond) + @cooldown_ms

    players =
      Map.new(s.players, fn {id, p} ->
        if p.side != "flat" and equity(p, mark) == 0,
          do: {id, %{p | side: "flat", bank: 0, leverage: 1, refill_at: deadline}},
          else: {id, p}
      end)

    record_mark(%{s | previous: s.mark, mark: mark, players: players})
  end

  defp fresh_player(mark),
    do: %{side: "flat", bank: @slug, entry: mark, leverage: 1, refill_at: nil}

  defp player(s, id), do: Map.get(s.players, id, fresh_player(s.mark))

  defp save_player(s, id, player) do
    next = %{s | players: Map.put(s.players, id, player)}
    {next, account(next, id)}
  end

  defp migrate_accounts(s) do
    players =
      Map.new(s.players, fn
        {_, %{leverage: _}} = current ->
          current

        {id, old} ->
          stake = min(old.bank, 10_000)

          change =
            case old.side do
              "flat" -> 0
              "up" -> s.mark - old.entry
              "down" -> old.entry - s.mark
            end

          bank = 50 * (old.bank + max(-stake, round(stake * change / old.entry)))
          deadline = if bank == 0, do: System.system_time(:millisecond) + @cooldown_ms
          {id, %{fresh_player(s.mark) | bank: bank, refill_at: deadline}}
      end)

    %{s | players: players}
  end

  defp equity(%{side: "flat", bank: bank}, _), do: bank

  defp equity(p, mark) do
    change = if p.side == "up", do: mark - p.entry, else: p.entry - mark
    pnl = p.bank * p.leverage * change
    rounded = div(abs(pnl) + div(p.entry, 2), p.entry)
    max(0, p.bank + if(pnl < 0, do: -rounded, else: rounded))
  end

  defp liquidation("flat", _, _, _), do: nil

  defp liquidation(side, entry, bank, leverage) do
    exposure = bank * leverage
    loss_numerator = bank * entry - div(entry, 2)
    distance = div(loss_numerator + exposure - 1, exposure)
    trigger = if side == "up", do: entry - distance, else: entry + distance
    if trigger in @min_mark..@max_mark, do: trigger
  end

  defp account(s, id) do
    p = player(s, id)

    balance = equity(p, s.mark)
    active = liquidation(p.side, p.entry, p.bank, p.leverage)

    quotes =
      for side <- ["up", "down"], into: %{} do
        triggers =
          cond do
            p.refill_at -> []
            p.side == side -> List.duplicate(active, 50)
            true -> Enum.map(1..50, &liquidation(side, s.mark, balance, &1))
          end

        {side, triggers}
      end

    remaining =
      if p.refill_at do
        div(max(0, p.refill_at - System.system_time(:millisecond)) + 999, 1000)
      end

    %{
      side: p.side,
      piss_coin: balance / 100,
      mark_cents: s.mark,
      entry_cents: if(p.side != "flat", do: p.entry),
      liquidation_cents: active,
      quotes_cents: quotes,
      leverage: p.leverage,
      refill_in: remaining,
      seat: String.slice(id, 0, 6)
    }
  end

  defp stage(s) do
    scene(s.display, s)
  end

  defp scene(display, s) do
    counts = Enum.frequencies_by(Map.values(s.players), & &1.side)
    up = Map.get(counts, "up", 0)
    down = Map.get(counts, "down", 0)

    %{
      mode: display.mode,
      widgets: display.widgets,
      melt: display.melt,
      hue: display.hue,
      gif: display.gif,
      brightness: display.brightness,
      mark_cents: s.mark,
      candles: Enum.reverse(s.candles),
      tickers:
        Enum.zip_with(@tickers, s.ticker_prices, fn {symbol, color, _}, price ->
          %{symbol: symbol, color: color, price_cents: price}
        end),
      mark: s.mark / 100,
      change: (s.mark - s.previous) / 100,
      up: up,
      down: down,
      held: s.held,
      volatility_bps: s.volatility_bps,
      layers: Display.layers(display)
    }
  end
end
