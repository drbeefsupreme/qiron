defmodule Qiron.Panel do
  use GenServer
  alias Qiron.{Display, Market}
  @modes %{"gif" => 0, "blood" => 1, "intro" => 2}
  defstruct port: nil,
            job: nil,
            prepared: nil,
            restore: :needed,
            failed: nil,
            last_chart: nil,
            staged_chart: nil

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

  def handle_call({:command, {:take, rev}}, _, s) do
    draft = Market.call(:panel)

    cond do
      rev !== draft.revision ->
        {:reply, :stale, s}

      !draft.dirty ->
        {:reply, :ok, s}

      !s.port ->
        {:reply, Market.call({:take, rev}), s}

      s.prepared != rev ->
        {:reply, :not_ready, s}

      true ->
        case transmit(s, {42, ""}) do
          {:ok, s} ->
            :ok = Market.call({:take, rev})
            {:reply, :ok, %{s | restore: :done, prepared: nil, last_chart: nil, failed: nil}}

          {reason, s} ->
            {:reply, reason, failure(s, {:draft, rev}, reason)}
        end
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
        s = if s.restore == :done and live.mode == "blood", do: sync_chart(s, live), else: s
        draft = Market.call(:panel)
        s = plan(s, draft)

        if s.prepared == draft.revision and draft.mode == "blood" do
          frame = field(chart(draft))

          if frame != s.staged_chart,
            do: send(self(), {:refresh_staged_chart, draft.revision, frame})
        end

        s
      else
        s
      end

    Process.send_after(self(), :sync, if(s.port, do: 300, else: 1200))
    {:noreply, s}
  end

  def handle_info({:refresh_staged_chart, rev, frame}, %{prepared: rev} = s) do
    case transmit(s, frame) do
      {:ok, s} -> {:noreply, %{s | staged_chart: frame}}
      {reason, s} -> {:noreply, failure(s, {:draft, rev}, reason, frame)}
    end
  end

  def handle_info({:prepare, key}, %{job: {key, [frame | rest]}} = s) do
    case transmit(s, frame) do
      {:ok, s} ->
        case {key, rest} do
          {{:restore, _}, []} ->
            {:noreply, plan(%{s | restore: :done, failed: nil, job: nil}, Market.call(:panel))}

          {{:draft, rev}, []} ->
            {:noreply, %{s | prepared: rev, staged_chart: frame, failed: nil, job: nil}}

          _ ->
            {:noreply, start_job(s, key, rest)}
        end

      {reason, s} ->
        {:noreply, failure(s, key, reason, frame)}
    end
  end

  def handle_info({port, {:exit_status, _}}, %{port: port} = s), do: {:noreply, disconnect(s)}
  def handle_info(_, s), do: {:noreply, s}

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
    fields =
      case data.mode do
        "gif" ->
          lines =
            Enum.flat_map(data.layers, fn l ->
              [{5 + l.id, <<l.speed>>}, {l.id - 1, <<-1::little-signed-32, l.text::binary>>}]
            end)

          gif = data.gif
          exact = if gif.playing and gif.file != "", do: [{39, gif.file}], else: []
          stop = if gif.playing, do: [], else: [{22, ""}]
          cue = if action, do: [{Display.method(action), ""}], else: []
          lines ++ stop ++ [{Display.method(gif.preset), ""}] ++ exact ++ cue

        "blood" ->
          [chart(data)]

        "intro" ->
          []
      end

    [
      {40, <<Map.fetch!(@modes, data.mode)>>}
      | Enum.map([{12, <<data.brightness>>} | fields], &field/1)
    ]
  end

  defp chart(data) do
    bars =
      for c <- data.candles,
          into: <<>>,
          do: <<c.open::little-32, c.high::little-32, c.low::little-32, c.close::little-32>>

    {38, <<data.mark_cents::little-32, data.up::little-32, data.down::little-32, bars::binary>>}
  end

  defp field({method, payload}), do: {41, <<method, payload::binary>>}

  defp sync_chart(s, data) do
    frame = chart(data)

    if frame == s.last_chart do
      s
    else
      case transmit(s, frame) do
        {:ok, s} -> %{s | last_chart: frame}
        {_, s} -> disconnect(s)
      end
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
          {^port, {:data, "R"}} -> %{s | port: port}
          {^port, {:exit_status, _}} -> s
        after
          1000 -> disconnect(%{s | port: port})
        end
    end
  end

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
