defmodule Qiron.Panel do
  use GenServer
  alias Qiron.{Display, Market}
  @modes %{"gif" => 0, "blood" => 1, "intro" => 2, "crow" => 3, "beef" => 4}
  defstruct port: nil,
            job: nil,
            prepared: nil,
            restore: :needed,
            failed: nil,
            live_fields: %{},
            staged_fields: %{}

  def start_link(opts), do: GenServer.start_link(__MODULE__, opts, name: __MODULE__)
  def command(cmd), do: GenServer.call(__MODULE__, {:command, cmd}, 12_000)
  def status, do: GenServer.call(__MODULE__, :status, 12_000)

  def init(_) do
    send(self(), :sync)
    {:ok, %__MODULE__{}}
  end

  def handle_call(:status, _, s) do
    draft = Market.call(:panel)

    readiness =
      cond do
        !s.port -> "offline"
        s.failed -> "error"
        s.prepared == draft.revision or (s.restore == :done and !draft.dirty) -> "ready"
        true -> "loading"
      end

    error = if s.failed, do: elem(s.failed, 1)

    {:reply,
     Map.merge(draft, %{
       status: if(s.port, do: "connected", else: "disconnected"),
       actions: Display.actions(),
       ready: readiness == "ready",
       readiness: readiness,
       error: error
     }), s}
  end

  def handle_call({:command, {:take, rev}}, _, s), do: take(rev, s)

  def handle_call({:command, {:live_fx, melt, hue} = cmd}, _, s)
      when melt in 0..100 and hue in 0..100 do
    cond do
      !s.port ->
        {:reply, Market.call(cmd), s}

      s.restore != :done ->
        {:reply, :not_ready, s}

      true ->
        case transmit(s, {45, <<melt, hue>>}) do
          {:ok, s} -> {:reply, Market.call(cmd), s}
          {error, s} -> {:reply, error, s}
        end
    end
  end

  def handle_call({:command, {:screen_cue, kind}}, _, s) when kind in ["crack", "stars"] do
    <<seed::little-32>> = :crypto.strong_rand_bytes(4)
    type = if kind == "crack", do: 1, else: 2
    live_command(s, {46, <<type, seed::little-32>>}, {:screen_cue, kind, seed})
  end

  def handle_call({:command, {:splice_seconds, seconds} = cmd}, _, s)
      when seconds in [0, 5, 60] do
    if seconds == Market.call(:splice_seconds) do
      {:reply, :ok, s}
    else
      live_command(s, {47, <<seconds>>}, cmd)
    end
  end

  def handle_call({:command, cmd}, _, s) do
    case Market.call(cmd) do
      :ok ->
        draft = Market.call(:panel)
        retry = match?({:gif, _, _}, cmd) and s.failed != nil

        s =
          if retry do
            restore = if s.restore == :failed and !draft.dirty, do: :needed, else: s.restore
            %{s | failed: nil, restore: restore}
          else
            s
          end

        {:reply, :ok, plan(s, draft)}

      error ->
        {:reply, error, s}
    end
  end

  def handle_info(:sync, s) do
    s = if s.port, do: s, else: connect(s)

    s =
      if s.port do
        live = Market.call(:live_panel)
        s = if s.restore == :done, do: sync_market(s, live), else: s
        draft = Market.call(:panel)
        s = plan(s, draft)

        if s.prepared == draft.revision do
          for {id, _} = frame <- market_fields(draft), s.staged_fields[id] != frame do
            send(self(), {:refresh_market, draft.revision, frame})
          end
        end

        s
      else
        s
      end

    Process.send_after(self(), :sync, if(s.port, do: 300, else: 1200))
    {:noreply, s}
  end

  def handle_info({:refresh_market, rev, {id, _} = frame}, %{prepared: rev} = s) do
    case transmit(s, field(frame)) do
      {:ok, s} -> {:noreply, %{s | staged_fields: Map.put(s.staged_fields, id, frame)}}
      {reason, s} -> {:noreply, failure(s, {:draft, rev}, reason, field(frame))}
    end
  end

  def handle_info({:prepare, key}, %{job: {key, [frame | rest]}} = s) do
    case transmit(s, frame) do
      {:ok, s} ->
        s =
          case frame do
            {41, <<id, payload::binary>>} when id in [38, 43, 49] ->
              %{s | staged_fields: Map.put(s.staged_fields, id, {id, payload})}

            _ ->
              s
          end

        case {key, rest} do
          {{:restore, _}, []} ->
            {:noreply, plan(%{s | restore: :done, failed: nil, job: nil}, Market.call(:panel))}

          {{:draft, rev}, []} ->
            {:noreply, %{s | prepared: rev, failed: nil, job: nil}}

          _ ->
            {:noreply, start_job(s, key, rest)}
        end

      {reason, s} ->
        {:noreply, failure(s, key, reason, frame)}
    end
  end

  def handle_info({port, {:exit_status, _}}, %{port: port} = s), do: {:noreply, disconnect(s)}
  def handle_info(_, s), do: {:noreply, s}

  defp take(rev, s) do
    draft = Market.call(:panel)

    cond do
      rev !== draft.revision ->
        {:reply, :stale, s}

      !draft.dirty and s.prepared != rev ->
        {:reply, :ok, s}

      !s.port ->
        {:reply, Market.call({:take, rev}), s}

      s.prepared != rev ->
        {:reply, :not_ready, s}

      true ->
        case transmit(s, {42, ""}) do
          {:ok, s} ->
            :ok = Market.call({:take, rev})
            {:reply, :ok, %{s | restore: :done, prepared: nil, live_fields: %{}, failed: nil}}

          {reason, s} ->
            {:reply, reason, failure(s, {:draft, rev}, reason)}
        end
    end
  end

  defp plan(%{port: nil} = s, _), do: s

  defp plan(s, draft) do
    cond do
      s.restore == :needed ->
        enqueue(s, {:restore, :live}, fn -> scene(Market.call(:live_panel), nil) ++ [{42, ""}] end)

      draft.dirty and s.prepared != draft.revision ->
        enqueue(s, {:draft, draft.revision}, fn -> scene(draft, draft.action) end)

      !draft.dirty and s.restore == :done ->
        %{s | job: nil, failed: nil, prepared: nil}

      true ->
        s
    end
  end

  defp enqueue(%{failed: {key, _}} = s, key, _), do: s
  defp enqueue(%{job: {key, _}} = s, key, _), do: s

  defp enqueue(s, key, commands),
    do: start_job(%{s | prepared: nil, failed: nil}, key, commands.())

  defp start_job(s, key, frames) do
    send(self(), {:prepare, key})
    %{s | job: {key, frames}}
  end

  defp failure(s, key, reason, frame \\ {42, ""})
  defp failure(s, _, :offline, _), do: s

  defp failure(s, key, :rejected, frame) do
    error =
      case frame do
        {41, <<39, path::binary>>} -> "Could not open " <> path <> " on the panel SD card."
        _ -> "Panel rejected scene. Check the SD card and firmware version."
      end

    restore = if match?({:restore, _}, key), do: :failed, else: s.restore
    %{s | failed: {key, error}, prepared: nil, job: nil, restore: restore}
  end

  defp scene(data, action) do
    stack = for widget <- data.widgets, into: <<>>, do: <<Display.widget_id(widget)>>
    fields = [{44, <<data.melt, data.hue, stack::binary>>}, {12, <<data.brightness>>}]

    lines =
      for l <- data.layers,
          Display.line_widget(l.id) in data.widgets,
          frame <- [{5 + l.id, <<l.speed>>}, {l.id - 1, <<-1::little-signed-32, l.text::binary>>}],
          do: frame

    gif_fields =
      if "sd" in data.widgets do
        gif = data.gif
        exact = if gif.playing and gif.file != "", do: [{39, gif.file}], else: []
        stop = if gif.playing, do: [], else: [{22, ""}]
        cue = if action, do: [{Display.method(action), ""}], else: []
        stop ++ [{Display.method(gif.preset), ""}] ++ exact ++ cue
      else
        []
      end

    staged = Enum.map(fields ++ lines ++ gif_fields ++ market_fields(data), &field/1)

    banners =
      for {id, banner} <- [{"join", :join_banner}, {"callin", :callin_banner}],
          id in data.widgets,
          do: {41, banner}

    [{40, <<Map.fetch!(@modes, data.mode)>>} | staged ++ banners]
  end

  defp market_fields(data) do
    charts = if "chart" in data.widgets, do: [chart(data)], else: []

    quotes =
      if "ticker" in data.widgets or "interest" in data.widgets do
        prices = for t <- data.tickers, into: <<>>, do: <<t.price_cents::little-32>>
        [{43, prices}]
      else
        []
      end

    summary =
      if "price" in data.widgets or "interest" in data.widgets do
        long = min(data.long_oi_cents, 0xFFFFFFFFFFFFFFFF)
        short = min(data.short_oi_cents, 0xFFFFFFFFFFFFFFFF)
        [{49, <<data.mark_cents::little-32, long::little-64, short::little-64>>}]
      else
        []
      end

    charts ++ quotes ++ summary
  end

  defp chart(data) do
    bars =
      for c <- data.candles,
          into: <<>>,
          do: <<c.open::little-32, c.high::little-32, c.low::little-32, c.close::little-32>>

    {38, <<data.mark_cents::little-32, data.up::little-32, data.down::little-32, bars::binary>>}
  end

  defp field({method, payload}), do: {41, <<method, payload::binary>>}

  defp sync_market(s, data) do
    Enum.reduce_while(market_fields(data), s, fn {id, _} = frame, s ->
      if s.live_fields[id] == frame do
        {:cont, s}
      else
        case transmit(s, frame) do
          {:ok, s} -> {:cont, %{s | live_fields: Map.put(s.live_fields, id, frame)}}
          {_, s} -> {:halt, disconnect(s)}
        end
      end
    end)
  end

  defp live_command(%{port: nil} = s, _, cmd), do: {:reply, Market.call(cmd), s}

  defp live_command(s, frame, cmd) do
    case transmit(s, frame) do
      {:ok, s} -> {:reply, Market.call(cmd), s}
      {reason, s} -> {:reply, reason, s}
    end
  end

  defp restore_splice(s) do
    seconds = Market.call(:splice_seconds)

    with {:ok, s} <- transmit(s, {47, <<0>>}),
         {:ok, s} <- if(seconds == 0, do: {:ok, s}, else: transmit(s, {47, <<seconds>>})) do
      :ok = Market.call(:splice_rearmed)
      s
    else
      {_, s} -> disconnect(s)
    end
  end

  defp connect(s) do
    device = System.get_env("QYRON_DEVICE", "/dev/ttyACM0")

    case File.exists?(device) && System.find_executable("python3") do
      missing when missing in [false, nil] ->
        s

      python ->
        bridge = Application.app_dir(:qiron, "priv/serial.py")

        port =
          Port.open({:spawn_executable, python}, [:binary, :exit_status, args: [bridge, device]])

        receive do
          {^port, {:data, "R"}} -> restore_splice(%{s | port: port})
          {^port, {:exit_status, _}} -> s
        after
          1000 -> disconnect(%{s | port: port})
        end
    end
  end

  defp transmit(s, {41, :callin_banner}), do: transmit(s, field({50, Display.callin_banner!()}))
  defp transmit(s, {41, :join_banner}), do: transmit(s, field({48, Display.join_banner!()}))

  defp transmit(%{port: port} = s, {method, payload}) do
    Port.command(port, <<254, method, byte_size(payload)::little-16, payload::binary>>)

    case ack(port, <<>>, System.monotonic_time(:millisecond) + 1500) do
      :ok -> {:ok, s}
      :rejected -> {:rejected, s}
      :offline -> {:offline, disconnect(s)}
    end
  rescue
    ArgumentError -> {:offline, disconnect(s)}
  end

  defp ack(_, <<254, 0>>, _), do: :ok
  defp ack(_, <<254, 1>>, _), do: :rejected

  defp ack(port, prefix, until) when prefix in [<<>>, <<254>>] do
    receive do
      {^port, {:data, bytes}} -> ack(port, prefix <> bytes, until)
      {^port, {:exit_status, _}} -> :offline
    after
      max(0, until - System.monotonic_time(:millisecond)) -> :offline
    end
  end

  defp ack(_, _, _), do: :offline

  defp disconnect(s) do
    if s.port && Port.info(s.port), do: Port.close(s.port)
    %__MODULE__{}
  end
end
