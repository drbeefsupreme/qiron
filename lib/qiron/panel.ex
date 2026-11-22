defmodule Qiron.Panel do
  use GenServer
  alias Qiron.Market

  @actions ~w(runFeatureDemo drawRandomShapes drawRandomPixels hitShapes hitPixels setBlackBackground setRedBackground toggleBlinking nextGif noGif enableGifsLoop disableGifsLoop gifK gifO gifF gifD gifJ gifS gifB gifT gifA gifP gifH clearLoops)
  @methods @actions |> Enum.with_index(13) |> Map.new()
  @macros ~w(caw dopamine clearText clear)
  def actions, do: @macros ++ @actions

  def start_link(opts), do: GenServer.start_link(__MODULE__, opts, name: __MODULE__)
  def action(name), do: GenServer.call(__MODULE__, {:action, name}, 12_000)
  def status, do: GenServer.call(__MODULE__, :status, 12_000)

  def init(_) do
    send(self(), :sync)
    {:ok, %{port: nil, applied: %{}}}
  end

  def handle_call(:status, _, s) do
    {:reply, if(s.port, do: "connected", else: "disconnected"), s}
  end

  def handle_call({:action, name}, _, s) when name in @macros do
    case {name, s.port} do
      {"clear", nil} ->
        {:reply, :offline, s}

      _ ->
        Market.call({:macro, name})

        if name == "clear" do
          {reply, s} =
            transmit(s, for(key <- ~w(noGif clearLoops disableGifsLoop), do: {@methods[key], ""}))

          {:reply, reply, s}
        else
          {:reply, :ok, s}
        end
    end
  end

  def handle_call({:action, name}, _, s) when is_map_key(@methods, name) do
    {reply, s} = transmit(s, [{@methods[name], ""}])
    {:reply, reply, s}
  end

  def handle_call({:action, _}, _, s), do: {:reply, :invalid, s}

  def handle_info(:sync, s) do
    s = if s.port, do: s, else: connect(s)

    s =
      if s.port do
        %{layers: layers, brightness: brightness} = Market.call(:panel)

        desired =
          [{12, <<brightness>>}] ++
            Enum.flat_map(layers, fn l ->
              [{5 + l.id, <<l.speed>>}, {l.id - 1, <<-1::little-signed-32, l.text::binary>>}]
            end)

        changes = Enum.reject(desired, fn {k, v} -> s.applied[k] == v end)

        case transmit(s, changes) do
          {:ok, s} -> %{s | applied: Map.new(desired)}
          {_, s} -> s
        end
      else
        s
      end

    Process.send_after(self(), :sync, if(s.port, do: 300, else: 1200))
    {:noreply, s}
  end

  def handle_info({port, {:exit_status, _}}, %{port: port} = s), do: {:noreply, disconnect(s)}
  def handle_info(_, s), do: {:noreply, s}

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

  defp transmit(%{port: nil} = s, _), do: {:offline, s}
  defp transmit(s, []), do: {:ok, s}

  defp transmit(%{port: port} = s, [{method, payload} | rest]) do
    Port.command(port, <<254, method, byte_size(payload)::little-16, payload::binary>>)

    case ack(port, <<>>, System.monotonic_time(:millisecond) + 1500) do
      :ok -> transmit(s, rest)
      reason -> {reason, disconnect(s)}
    end
  rescue
    ArgumentError -> {:offline, disconnect(s)}
  end

  defp ack(_, <<254, 0>>, _), do: :ok

  defp ack(port, prefix, until) when prefix in [<<>>, <<254>>] do
    receive do
      {^port, {:data, bytes}} -> ack(port, prefix <> bytes, until)
      {^port, {:exit_status, _}} -> :offline
    after
      max(0, until - System.monotonic_time(:millisecond)) -> :offline
    end
  end

  defp ack(_, _, _), do: :rejected

  defp disconnect(s) do
    if s.port && Port.info(s.port), do: Port.close(s.port)
    %{s | port: nil, applied: %{}}
  end
end
