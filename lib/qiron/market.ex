defmodule Qiron.Market do
  use GenServer

  @slug 5_000_000
  @cooldown_ms 300_000

  defstruct mark: 10000,
            previous: 10000,
            held: false,
            players: %{},
            lines: %{},
            speeds: %{},
            brightness: 255

  def start_link(opts), do: GenServer.start_link(__MODULE__, opts, Keyword.take(opts, [:name]))
  def call(command, server \\ __MODULE__), do: GenServer.call(server, command)

  def init(opts) do
    path = Keyword.fetch!(opts, :path)

    show =
      case File.read(path) do
        {:ok, bytes} -> Map.merge(%__MODULE__{}, :erlang.binary_to_term(bytes, [:safe]))
        {:error, :enoent} -> %__MODULE__{}
      end

    if Keyword.get(opts, :tick, true), do: Process.send_after(self(), :tick, 2000)
    {:ok, persist(migrate_accounts(show), show, path)}
  end

  def handle_info(:tick, {s, path}) do
    next =
      if s.held, do: s, else: move(s, round(s.mark * (1 + (:rand.uniform(101) - 51) / 10000)))

    Process.send_after(self(), :tick, 2000)
    {:noreply, persist(next, s, path)}
  end

  def handle_call(command, _, {s, path}) do
    {next, reply} = apply_command(command, s)
    {:reply, reply, persist(next, s, path)}
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
  defp apply_command({:mark, cents}, s) when cents in 100..1_000_000, do: {move(s, cents), :ok}

  defp apply_command({:nudge, dir}, s) when dir in [-1, 1],
    do: {move(s, round(s.mark * (1 + dir * 0.05))), :ok}

  defp apply_command(:panel, s) do
    layers =
      stage(s).layers ++
        [%{id: 6, text: Map.get(s.lines, 6, ""), override: Map.get(s.lines, 6, "")}]

    defaults = [10, 20, 40, 80, 120, 40]

    layers =
      Enum.zip_with(layers, defaults, fn l, speed ->
        Map.put(l, :speed, Map.get(s.speeds, l.id, speed))
      end)

    {s, %{brightness: s.brightness, layers: layers}}
  end

  defp apply_command({:line, layer, text}, s)
       when layer in 1..6 and is_binary(text) and byte_size(text) <= 32767 do
    if String.valid?(text) and not String.contains?(text, <<0>>) do
      lines = if text == "", do: Map.delete(s.lines, layer), else: Map.put(s.lines, layer, text)
      {%{s | lines: lines}, :ok}
    else
      {s, :invalid}
    end
  end

  defp apply_command({:speed, layer, speed}, s) when layer in 1..6 and speed in 0..255,
    do: {%{s | speeds: Map.put(s.speeds, layer, speed)}, :ok}

  defp apply_command({:brightness, value}, s) when value in 0..255,
    do: {%{s | brightness: value}, :ok}

  defp apply_command({:macro, name}, s) when name in ["clear", "clearText"] do
    {%{s | lines: Map.merge(s.lines, Map.new(1..5, &{&1, ""}))}, :ok}
  end

  defp apply_command({:macro, name}, s) when name in ["caw", "dopamine"] do
    lines = Enum.with_index(macro_lines(name), 1) |> Map.new(fn {text, i} -> {i, text} end)
    speeds = Map.new(1..5, &{&1, :rand.uniform(99)})
    {%{s | lines: Map.merge(s.lines, lines), speeds: Map.merge(s.speeds, speeds)}, :ok}
  end

  defp apply_command(_, s), do: {s, :invalid}

  defp macro_lines("caw"),
    do: [
      "CAWCAWCAWCAWCAWCAWCAWCAWCAWCAWCAWCAWCAWCAWCAWCAWCAWCAWCAWCAWCAWCAWCAWCAW",
      "CAW CAW CAW CAW CAW CAW CAW CAW CAW CAW CAW CAW CAW CAW CAW CAW CAW CAW CAW CAW CAW CAW CAW CAW",
      "CAW CAW CAW CAW CAW CAW CAW CAW CAW CAW CAW CAW CAW CAW CAW CAW CAW CAW CAW CAW CAW CAW CAW CAW",
      "CAWCAWCAWCAWCAWCAWCAWCAWCAWCAWCAWCAWCAWCAWCAWCAWCAWCAWCAWCAWCAWCAWCAWCAW",
      "CAW"
    ]

  defp macro_lines("dopamine"),
    do: [
      "DOPAMINE DOPAMINE DOPAMINE DOPAMINE DOPAMINE DOPAMINE DOPAMINE DOPAMINE DOPAMINE DOPAMINE DOPAMINE DOPAMINE DOPAMINE DOPAMINE DOPAMINE ",
      "DOPAMINE DOPAMINE DOPAMINE DOPAMINE DOPAMINE DOPAMINE DOPAMINE DOPAMINE DOPAMINE DOPAMINE DOPAMINE DOPAMINE DOPAMINE DOPAMINE DOPAMINE DOPAMINE DOPAMINE DOPAMINE DOPAMINE DOPAMINE DOPAMINE",
      "DOPAMINE DOPAMINE DOPAMINE DOPAMINE DOPAMINE DOPAMINE DOPAMINE DOPAMINE DOPAMINE DOPAMINE DOPAMINE DOPAMINE DOPAMINE DOPAMINE DOPAMINE DOPAMINE DOPAMINE DOPAMINE DOPAMINE DOPAMINE DOPAMINE",
      "DOPAMINE DOPAMINE DOPAMINE DOPAMINE DOPAMINE DOPAMINE DOPAMINE DOPAMINE DOPAMINE DOPAMINE DOPAMINE DOPAMINE DOPAMINE DOPAMINE DOPAMINE DOPAMINE DOPAMINE DOPAMINE DOPAMINE DOPAMINE DOPAMINE",
      "DOPAMINE DOPAMINE DOPAMINE DOPAMINE DOPAMINE DOPAMINE DOPAMINE DOPAMINE DOPAMINE DOPAMINE DOPAMINE DOPAMINE DOPAMINE DOPAMINE DOPAMINE DOPAMINE DOPAMINE DOPAMINE DOPAMINE DOPAMINE DOPAMINE"
    ]

  defp move(s, cents) do
    mark = min(1_000_000, max(100, cents))

    deadline = System.system_time(:millisecond) + @cooldown_ms

    players =
      Map.new(s.players, fn {id, p} ->
        if p.side != "flat" and equity(p, mark) == 0,
          do: {id, %{p | side: "flat", bank: 0, leverage: 1, refill_at: deadline}},
          else: {id, p}
      end)

    %{s | previous: s.mark, mark: mark, players: players}
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

  defp account(s, id) do
    p = player(s, id)

    remaining =
      if p.refill_at do
        div(max(0, p.refill_at - System.system_time(:millisecond)) + 999, 1000)
      end

    %{
      side: p.side,
      piss_coin: equity(p, s.mark) / 100,
      leverage: p.leverage,
      refill_in: remaining,
      seat: String.slice(id, 0, 6)
    }
  end

  defp stage(s) do
    counts = Enum.frequencies_by(Map.values(s.players), & &1.side)
    up = Map.get(counts, "up", 0)
    down = Map.get(counts, "down", 0)

    defaults = [
      "CROW BLOOD  #{:erlang.float_to_binary(s.mark / 100, decimals: 2)}",
      "UP  #{up}    DOWN  #{down}",
      "TOO LATE SHOW",
      "BLOOD",
      "PERP"
    ]

    layers =
      for {msg, i} <- Enum.with_index(defaults, 1),
          do: %{id: i, text: Map.get(s.lines, i, msg), override: Map.get(s.lines, i, "")}

    %{
      mark: s.mark / 100,
      change: (s.mark - s.previous) / 100,
      up: up,
      down: down,
      held: s.held,
      layers: layers
    }
  end
end
