defmodule Qiron.Display do
  @ids ~w(sd chart intro crow beef peter santa ticker line1 line2 line3 line4 line5 lineF)
       |> Enum.with_index()
       |> Map.new()
  @gif_widgets ~w(sd line1 line2 line3 line4 line5 lineF)
  @defaults %{
    "gif" => @gif_widgets,
    "blood" => ~w(chart ticker),
    "intro" => ["intro"],
    "crow" => ["crow"],
    "beef" => ["beef"]
  }
  @template_keys [:widgets, :melt, :hue, :lines, :speeds, :gif]

  defstruct templates: %{},
            widgets: @gif_widgets,
            melt: 0,
            hue: 0,
            mode: "gif",
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

  def widget_id(widget), do: Map.fetch!(@ids, widget)
  def line_widget(6), do: "lineF"
  def line_widget(id), do: "line#{id}"

  def restore(%{widgets: _} = d), do: d

  def restore(old) do
    d = struct(__MODULE__, Map.take(old, [:brightness, :lines, :speeds, :gif]))
    {:ok, restored} = change(d, {:mode, Map.get(old, :mode, "gif")})
    restored
  end

  defp template(mode),
    do: Map.take(%__MODULE__{widgets: Map.fetch!(@defaults, mode)}, @template_keys)

  def remember_live_fx(draft, live, melt, hue) do
    saved = Map.get_lazy(draft.templates, live.mode, fn -> template(live.mode) end)

    if draft.mode != live.mode and {saved.melt, saved.hue} == {live.melt, live.hue} do
      updated = %{saved | melt: melt, hue: hue}
      templates = save_template(draft.templates, live.mode, updated)
      %{draft | templates: templates}
    else
      draft
    end
  end

  defp save_template(templates, mode, value) do
    if value == template(mode),
      do: Map.delete(templates, mode),
      else: Map.put(templates, mode, value)
  end

  def cue(d, name) do
    if "sd" in d.widgets or is_nil(name) or
         (name in ["caw", "dopamine", "clearText"] and
            Enum.any?(d.widgets, &String.starts_with?(&1, "line"))) do
      apply_cue(d, name)
    else
      :wrong_mode
    end
  end

  defp apply_cue(_, name) when not is_binary(name) and not is_nil(name), do: :invalid
  defp apply_cue(d, nil), do: {:ok, d, nil}

  defp apply_cue(d, name) when name in ["caw", "dopamine", "clearText", "clear"] do
    {:ok, next} = change(d, {:macro, name})
    {:ok, next, if(name == "clear", do: "clearLoops")}
  end

  defp apply_cue(d, preset) when is_map_key(@folders, preset),
    do: {:ok, %{d | gif: %{preset: preset, file: "", playing: true}}, nil}

  defp apply_cue(d, name)
       when name in ["nextGif", "noGif", "enableGifsLoop", "disableGifsLoop", "clearLoops"] do
    play = name in ["nextGif", "enableGifsLoop"]
    {:ok, next} = change(d, {:playing, play})
    {:ok, next, if(name in ["nextGif", "clearLoops"], do: name)}
  end

  defp apply_cue(d, name) when name in @effects, do: {:ok, d, name}
  defp apply_cue(_, _), do: :invalid

  def layers(display) do
    for {speed, id} <- Enum.with_index([10, 20, 40, 80, 120, 40], 1) do
      text = Map.get(display.lines, id, "")
      %{id: id, speed: Map.get(display.speeds, id, speed), text: text, override: text}
    end
  end

  def change(%{mode: mode} = d, {:mode, mode}), do: {:ok, d}

  def change(d, {:mode, mode}) when is_map_key(@defaults, mode) do
    current = Map.take(d, @template_keys)

    saved = save_template(d.templates, d.mode, current)
    {next, saved} = Map.pop_lazy(saved, mode, fn -> template(mode) end)
    {:ok, struct!(%{d | mode: mode, templates: saved}, next)}
  end

  def change(d, {:widgets, widgets}) when is_list(widgets) do
    if length(widgets) <= map_size(@ids) and Enum.uniq(widgets) == widgets and
         Enum.all?(widgets, &Map.has_key?(@ids, &1)),
       do: {:ok, %{d | widgets: widgets}},
       else: :invalid
  end

  def change(d, {:fx, melt, hue}) when melt in 0..100 and hue in 0..100,
    do: {:ok, %{d | melt: melt, hue: hue}}

  def change(d, {:melt, melt}), do: change(d, {:fx, melt, d.hue})
  def change(d, {:hue, hue}), do: change(d, {:fx, d.melt, hue})
  def change(d, {:brightness, value}) when value in 0..255, do: {:ok, %{d | brightness: value}}

  def change(d, {:speed, id, speed}) when id in 1..6 and speed in 0..255,
    do:
      if(line_widget(id) in d.widgets,
        do: {:ok, %{d | speeds: Map.put(d.speeds, id, speed)}},
        else: :wrong_mode
      )

  def change(d, {:line, id, text})
      when id in 1..6 and is_binary(text) and byte_size(text) <= 32767 do
    cond do
      line_widget(id) not in d.widgets ->
        :wrong_mode

      String.valid?(text) and not String.contains?(text, <<0>>) ->
        {:ok, %{d | lines: Map.put(d.lines, id, text)}}

      true ->
        :invalid
    end
  end

  def change(d, {:gif, preset, file})
      when is_map_key(@folders, preset) and is_binary(file) and byte_size(file) <= 240 do
    cond do
      "sd" not in d.widgets ->
        :wrong_mode

      file == "" or valid_file?(file, @folders[preset]) ->
        {:ok, %{d | gif: %{preset: preset, file: file, playing: true}}}

      true ->
        :invalid
    end
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
