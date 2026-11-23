defmodule Qiron.Market do
  use GenServer
  alias Qiron.{Display, PnlHistory}

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
            presets: %{},
            blood_layout_version: 2,
            revision: 0,
            pending_action: nil,
            candles: [],
            splice_seconds: 0,
            ticker_seed: nil,
            ticker_prices: Enum.map(@tickers, &elem(&1, 2))

  def start_link(opts), do: GenServer.start_link(__MODULE__, opts, Keyword.take(opts, [:name]))
  def call(command, server \\ __MODULE__), do: GenServer.call(server, command)

  def init(opts) do
    Code.ensure_loaded!(PnlHistory)
    Display.join_banner!()
    Display.callin_banner!()
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

    saved_draft = Map.get(show, :draft) || display
    draft = Display.restore(saved_draft)

    presets =
      case Map.get(show, :presets) do
        p when is_map(p) and map_size(p) > 0 -> p
        _ -> Display.restore_presets(saved_draft, draft)
      end

    next = struct(__MODULE__, Map.delete(show, :__struct__))
    next = %{next | display: Display.restore(display), draft: draft, presets: presets}

    next =
      if Map.get(show, :blood_layout_version, 1) < 2 do
        presets =
          Map.update!(presets, "blood", fn saved ->
            %{saved | scene: Display.migrate_blood_widgets(saved.scene)}
          end)

        %{
          next
          | display: Display.migrate_blood_widgets(next.display),
            draft: Display.migrate_blood_widgets(next.draft),
            presets: presets,
            blood_layout_version: 2
        }
      else
        next
      end

    restored = persist(next |> migrate_accounts() |> record_mark(), show, path)
    {:ok, {restored, path, arm_splice(%{cue: nil})}}
  end

  def handle_info(:tick, {s, path, fx}) do
    next =
      if s.held do
        s |> observe_players(s.mark) |> record_mark()
      else
        step = :rand.uniform(2 * s.volatility_bps + 1) - s.volatility_bps - 1
        move(s, div(s.mark * (10_000 + step) + 5_000, 10_000))
      end

    seed = if s.ticker_seed, do: :rand.seed_s(s.ticker_seed), else: :rand.seed_s(:exsss)
    {prices, seed} = Enum.map_reduce(s.ticker_prices, seed, &tick_price/2)
    next = %{next | ticker_prices: prices, ticker_seed: :rand.export_seed_s(seed)}
    Process.send_after(self(), :tick, 2000)
    {:noreply, {persist(next, s, path), path, fx}}
  end

  def handle_call({:screen_cue, kind, seed}, _, {s, path, fx})
      when kind in ["crack", "stars"] and seed in 0..0xFFFFFFFF do
    {:reply, :ok, {s, path, %{fx | cue: {kind, seed, now_ms()}}}}
  end

  def handle_call({:splice_seconds, seconds}, _, {s, path, fx}) when seconds in [0, 5, 60] do
    if seconds == s.splice_seconds do
      {:reply, :ok, {s, path, fx}}
    else
      next = persist(%{s | splice_seconds: seconds}, s, path)
      {:reply, :ok, {next, path, arm_splice(fx)}}
    end
  end

  def handle_call(:splice_seconds, _, {s, _, _} = state), do: {:reply, s.splice_seconds, state}

  def handle_call(:splice_rearmed, _, {s, path, fx}),
    do: {:reply, :ok, {s, path, arm_splice(fx)}}

  def handle_call(command, _, {s, _, fx} = state) when command in [:stage, :panel, :live_panel] do
    {_, scene} = apply_command(command, s)
    now = now_ms()

    cue =
      case fx.cue do
        {kind, seed, at} when now - at < 10_000 -> %{kind: kind, seed: seed, elapsed_ms: now - at}
        _ -> nil
      end

    {:reply,
     Map.merge(scene, %{
       screen_cue: cue,
       splice_seconds: s.splice_seconds,
       splice_generation: fx.splice_generation,
       splice_elapsed_ms: if(s.splice_seconds == 0, do: 0, else: now - fx.splice_at)
     }), state}
  end

  def handle_call(command, _, {s, path, fx}) do
    {next, reply} = apply_command(command, s)
    {:reply, reply, {persist(next, s, path), path, fx}}
  end

  defp tick_price(price, seed) do
    {step, seed} = :rand.uniform_s(max(1, div(price, 50)), seed)
    {direction, seed} = :rand.uniform_s(2, seed)
    next = if direction == 1, do: max(1, price - step), else: min(@max_mark, price + step)
    {next, seed}
  end

  defp now_ms, do: System.monotonic_time(:millisecond)

  defp arm_splice(fx) do
    <<id::48>> = :crypto.strong_rand_bytes(6)
    Map.merge(fx, %{splice_at: now_ms(), splice_generation: id + 1})
  end

  defp persist(s, s, _path), do: s

  defp persist(next, _, path) do
    File.mkdir_p!(Path.dirname(path))
    File.write!(path <> ".tmp", :erlang.term_to_binary(next), [:sync])
    File.rename!(path <> ".tmp", path)
    next
  end

  defp apply_command(:stage, s), do: {s, stage(s)}

  defp apply_command({:account, id}, s) do
    {s, p, at} = seat(s, id)
    {s, account(s, id, p, at)}
  end

  defp apply_command({:trade, id, side, leverage}, s)
       when side in ["up", "down", "flat"] and leverage in 1..50 do
    {s, p, at} = seat(s, id)

    cond do
      p.refill_at != nil ->
        {s, :liquidated}

      p.side == side ->
        {s, account(s, id, p, at)}

      true ->
        position = if side == "flat", do: nil, else: new_position_id()
        settle_position(s, id, Map.put(p, :position_id, position), side, leverage, at)
    end
  end

  defp apply_command({:leverage, id, position, leverage}, s)
       when is_binary(position) and leverage in 1..50 do
    {s, p, at} = seat(s, id)

    cond do
      p.side == "flat" or p.position_id != position -> {s, :position_changed}
      p.leverage == leverage -> {s, account(s, id, p, at)}
      true -> settle_position(s, id, p, p.side, leverage, at)
    end
  end

  defp apply_command({:refill, id}, s) do
    case s.players[id] do
      %{refill_at: deadline} when is_integer(deadline) ->
        if System.system_time(:millisecond) >= deadline,
          do: apply_command({:account, id}, s),
          else: {s, :liquidated}

      _ ->
        {s, :invalid}
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
       live_preset_id: s.display.preset_id,
       presets: Display.preset_list(s.presets),
       live_melt: s.display.melt,
       live_hue: s.display.hue,
       action: s.pending_action
     })}
  end

  defp apply_command(:live_panel, s), do: {s, scene(s.display, s)}

  defp apply_command({:mode, mode}, s) do
    if Display.builtin?(mode), do: apply_command({:preset, mode}, s), else: {s, :invalid}
  end

  defp apply_command({:preset, id}, s) do
    case Map.fetch(s.presets, id) do
      {:ok, _} when id == s.draft.preset_id -> {s, :ok}
      {:ok, preset} -> edit(s, preset.scene, nil)
      :error -> {s, :invalid}
    end
  end

  defp apply_command({:save_as, raw}, s) when is_binary(raw) do
    name = raw |> String.trim() |> String.normalize(:nfc)

    cond do
      String.length(name) not in 1..48 or String.match?(name, ~r/\p{Cc}/u) ->
        {s, :invalid_preset_name}

      Enum.any?(s.presets, fn {_, preset} ->
        String.downcase(preset.name) == String.downcase(name)
      end) ->
        {s, :duplicate_preset_name}

      true ->
        id = "stack-" <> Base.url_encode64(:crypto.strong_rand_bytes(12), padding: false)
        draft = %{s.draft | preset_id: id}
        presets = Map.put(s.presets, id, %{name: name, scene: draft})
        edit(%{s | presets: presets}, draft, s.pending_action)
    end
  end

  defp apply_command({:live_fx, melt, hue}, s) when melt in 0..100 and hue in 0..100 do
    live = %{s.display | melt: melt, hue: hue}
    id = live.preset_id
    saved = s.presets[id].scene
    clean = s.draft == s.display and is_nil(s.pending_action)

    presets =
      if clean or
           (s.draft.preset_id != id and {saved.melt, saved.hue} == {s.display.melt, s.display.hue}) do
        put_in(s.presets, [id, :scene], %{saved | melt: melt, hue: hue})
      else
        s.presets
      end

    {%{s | display: live, draft: if(clean, do: live, else: s.draft), presets: presets}, :ok}
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
    do:
      {%{
         s
         | draft: draft,
           presets: put_in(s.presets, [draft.preset_id, :scene], draft),
           pending_action: action,
           revision: s.revision + 1
       }, :ok}

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

    next = observe_players(s, mark)
    record_mark(%{next | previous: s.mark, mark: mark})
  end

  defp observe_players(s, mark) do
    at = System.system_time(:millisecond)

    players =
      Map.new(s.players, fn {id, p} ->
        p =
          cond do
            p.refill_at ->
              refill_when_due(p, mark, at)

            p.side == "flat" ->
              p

            true ->
              case equity(p, mark) do
                0 ->
                  %{
                    p
                    | side: "flat",
                      bank: 0,
                      leverage: 1,
                      refill_at: at + @cooldown_ms,
                      pnl_runs: PnlHistory.finish(p.pnl_runs, at, -@slug)
                  }

                amount ->
                  %{p | pnl_runs: PnlHistory.sample(p.pnl_runs, at, amount - @slug)}
              end
          end

        {id, p}
      end)

    %{s | players: players}
  end

  defp fresh_player(mark),
    do: %{side: "flat", bank: @slug, entry: mark, leverage: 1, refill_at: nil}

  defp refill_when_due(%{refill_at: deadline} = p, mark, at)
       when is_integer(deadline) and deadline <= at do
    Map.put(fresh_player(mark), :pnl_runs, PnlHistory.start(p.pnl_runs, deadline, 0))
  end

  defp refill_when_due(p, _, _), do: p

  defp seat(s, id) do
    at = System.system_time(:millisecond)

    p =
      case Map.fetch(s.players, id) do
        {:ok, existing} -> refill_when_due(existing, s.mark, at)
        :error -> Map.put(fresh_player(s.mark), :pnl_runs, PnlHistory.start([], at, 0))
      end

    {%{s | players: Map.put(s.players, id, p)}, p, at}
  end

  defp new_position_id, do: Base.url_encode64(:crypto.strong_rand_bytes(12), padding: false)

  defp settle_position(s, id, p, side, leverage, at) do
    bank = equity(p, s.mark)

    next = %{
      p
      | side: side,
        bank: bank,
        entry: s.mark,
        leverage: if(side == "flat", do: 1, else: leverage),
        pnl_runs: PnlHistory.sample(p.pnl_runs, at, bank - @slug)
    }

    s = %{s | players: Map.put(s.players, id, next)}
    {s, account(s, id, next, at)}
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

    at = System.system_time(:millisecond)

    players =
      Map.new(players, fn {id, p} ->
        p =
          if Map.has_key?(p, :pnl_runs) do
            p
          else
            runs =
              if p.refill_at do
                ended = p.refill_at - @cooldown_ms
                [] |> PnlHistory.start(ended, -@slug) |> PnlHistory.finish(ended, -@slug)
              else
                PnlHistory.start([], at, equity(p, s.mark) - @slug)
              end

            Map.put(p, :pnl_runs, runs)
          end

        p =
          if p.side == "flat", do: p, else: Map.put_new_lazy(p, :position_id, &new_position_id/0)

        {id, refill_when_due(p, s.mark, at)}
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

  defp account(s, id, p, at) do
    balance = equity(p, s.mark)
    active = liquidation(p.side, p.entry, p.bank, p.leverage)

    quotes =
      for side <- ["up", "down"], into: %{} do
        triggers =
          for lev <- 1..50, is_nil(p.refill_at) do
            if {side, lev} == {p.side, p.leverage},
              do: active,
              else: liquidation(side, s.mark, balance, lev)
          end

        {side, triggers}
      end

    remaining =
      if p.refill_at do
        div(max(0, p.refill_at - at) + 999, 1000)
      end

    %{
      pnl_runs: PnlHistory.public(p.pnl_runs),
      as_of_ms: at,
      side: p.side,
      piss_coin: balance / 100,
      mark_cents: s.mark,
      position_id: if(p.side != "flat", do: p.position_id),
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
    {up, down, long_oi, short_oi} =
      Enum.reduce(s.players, {0, 0, 0, 0}, fn
        {_, %{side: "flat"}}, totals ->
          totals

        {_, p}, {up, down, long, short} ->
          notional = div(p.bank * p.leverage * s.mark + div(p.entry, 2), p.entry)

          if p.side == "up",
            do: {up + 1, down, long + notional, short},
            else: {up, down + 1, long, short + notional}
      end)

    scene = %{
      mode: display.mode,
      preset_id: display.preset_id,
      preset_name: Map.fetch!(s.presets, display.preset_id).name,
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
      long_oi_cents: long_oi,
      short_oi_cents: short_oi,
      held: s.held,
      volatility_bps: s.volatility_bps,
      layers: Display.layers(display)
    }

    Enum.reduce(display.widgets, scene, fn
      "join", scene -> Map.put(scene, :join_banner, Display.join_banner!())
      "callin", scene -> Map.put(scene, :callin_banner, Display.callin_banner!())
      _, scene -> scene
    end)
  end
end
