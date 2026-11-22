defmodule Qiron.Display do
  defstruct mode: "gif",
            brightness: 255,
            lines: %{},
            speeds: %{},
            gif: %{preset: "gifJ", file: "", playing: true}

  @folders %{
    "gifK" => "koyaanisqatsi",
    "gifO" => "obama",
    "gifF" => "flag",
    "gifD" => "drugs",
    "gifJ" => "joker",
    "gifS" => "spooky",
    "gifB" => "subgenius",
    "gifT" => "transparent",
    "gifA" => "aj",
    "gifP" => "blue",
    "gifH" => "hank"
  }

  @effects ~w(runFeatureDemo drawRandomShapes drawRandomPixels hitShapes hitPixels setBlackBackground setRedBackground toggleBlinking nextGif noGif enableGifsLoop disableGifsLoop gifK gifO gifF gifD gifJ gifS gifB gifT gifA gifP gifH clearLoops)
  @methods @effects |> Enum.with_index(13) |> Map.new()
  def actions, do: ~w(caw dopamine clearText clear) ++ @effects
  def method(name), do: Map.fetch!(@methods, name)

  def cue(_, name) when not is_binary(name) and not is_nil(name), do: :invalid
  def cue(%{mode: mode}, _) when mode != "gif", do: :wrong_mode
  def cue(d, nil), do: {:ok, d, nil}

  def cue(d, name) when name in ["caw", "dopamine", "clearText", "clear"] do
    {:ok, next} = change(d, {:macro, name})
    {:ok, next, if(name == "clear", do: "clearLoops")}
  end

  def cue(d, preset) when is_map_key(@folders, preset),
    do: {:ok, %{d | gif: %{preset: preset, file: "", playing: true}}, nil}

  def cue(d, name)
      when name in ["nextGif", "noGif", "enableGifsLoop", "disableGifsLoop", "clearLoops"] do
    play = name in ["nextGif", "enableGifsLoop"]
    {:ok, next} = change(d, {:playing, play})
    {:ok, next, if(name in ["nextGif", "clearLoops"], do: name)}
  end

  def cue(d, name) when name in @effects, do: {:ok, d, name}
  def cue(_, _), do: :invalid

  def layers(display) do
    for {speed, id} <- Enum.with_index([10, 20, 40, 80, 120, 40], 1) do
      text = Map.get(display.lines, id, "")
      %{id: id, speed: Map.get(display.speeds, id, speed), text: text, override: text}
    end
  end

  def change(d, {:mode, mode}) when mode in ["gif", "blood", "intro", "crow", "beef"],
    do: {:ok, %{d | mode: mode}}

  def change(d, {:brightness, value}) when value in 0..255, do: {:ok, %{d | brightness: value}}
  def change(%{mode: mode}, _) when mode != "gif", do: :wrong_mode

  def change(d, {:speed, id, speed}) when id in 1..6 and speed in 0..255,
    do: {:ok, %{d | speeds: Map.put(d.speeds, id, speed)}}

  def change(d, {:line, id, text})
      when id in 1..6 and is_binary(text) and byte_size(text) <= 32767 do
    if String.valid?(text) and not String.contains?(text, <<0>>),
      do: {:ok, %{d | lines: Map.put(d.lines, id, text)}},
      else: :invalid
  end

  def change(d, {:gif, preset, file})
      when is_map_key(@folders, preset) and is_binary(file) and byte_size(file) <= 240 do
    if file == "" or valid_file?(file, @folders[preset]),
      do: {:ok, %{d | gif: %{preset: preset, file: file, playing: true}}},
      else: :invalid
  end

  def change(d, {:playing, false}), do: {:ok, %{d | gif: %{d.gif | playing: false}}}
  def change(d, {:playing, true}), do: {:ok, %{d | gif: %{d.gif | playing: true, file: ""}}}

  def change(d, {:macro, name}) when name in ["clear", "clearText"] do
    gif = if name == "clear", do: %{d.gif | playing: false}, else: d.gif
    {:ok, %{d | lines: Map.drop(d.lines, Enum.to_list(1..5)), gif: gif}}
  end

  def change(d, {:macro, name}) when name in ["caw", "dopamine"] do
    lines = Enum.with_index(macro_lines(name), 1) |> Map.new(fn {text, i} -> {i, text} end)
    speeds = Map.new(1..5, &{&1, :rand.uniform(99)})
    {:ok, %{d | lines: Map.merge(d.lines, lines), speeds: Map.merge(d.speeds, speeds)}}
  end

  def change(_, _), do: :invalid

  defp valid_file?(file, folder) do
    case String.split(file, "/") do
      ["", "gifs", ^folder, name] ->
        String.valid?(name) and String.length(name) > 4 and
          String.ends_with?(String.downcase(name), ".gif") and
          not String.starts_with?(name, ".") and not String.contains?(name, ["\\", <<0>>]) and
          not String.match?(name, ~r/[[:cntrl:]]/)

      _ ->
        false
    end
  end

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
end
