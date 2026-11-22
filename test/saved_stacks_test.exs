defmodule Qiron.SavedStacksTest do
  use ExUnit.Case, async: true
  alias Qiron.{Market, Display}

  @tag :tmp_dir
  test "independent copies stage, take, and restore under the same firmware mode", %{tmp_dir: dir} do
    opts = [path: Path.join(dir, "show"), tick: false]
    pid = start_supervised!({Market, opts})
    call = &Market.call(&1, pid)
    builtins = call.(:panel).presets
    assert Enum.map(builtins, & &1.id) == ~w(gif blood intro crow beef)
    assert :ok = call.({:widgets, ["line1", "sd", "join"]})
    assert :ok = call.({:line, 1, "A"})
    assert :ok = call.({:speed, 1, 78})
    assert :ok = call.({:gif, "gifS", "/gifs/spooky/snow.gif"})
    assert :ok = call.({:brightness, 101})
    assert :ok = call.({:fx, 10, 20})
    assert :ok = call.({:save_as, "  Holiday A  "})

    assert %{
             preset_id: a,
             preset_name: "Holiday A",
             mode: "gif",
             dirty: true,
             live_preset_id: "gif"
           } = call.(:panel)

    assert a =~ ~r/^stack-[A-Za-z0-9_-]+$/
    assert call.(:stage).preset_id == "gif"
    assert :ok = call.({:take, call.(:panel).revision})
    assert :ok = call.({:save_as, "Holiday B"})
    assert %{preset_id: b, live_preset_id: ^a, dirty: true} = call.(:panel)
    assert a != b
    assert :ok = call.({:widgets, ["sd", "line1"]})
    assert :ok = call.({:line, 1, "B"})
    assert :ok = call.({:brightness, 202})
    assert :ok = call.({:fx, 33, 44})
    rev = call.(:panel).revision
    assert :ok = call.({:live_fx, 75, 66})

    assert %{
             preset_id: ^a,
             preset_name: "Holiday A",
             melt: 75,
             hue: 66,
             layers: [%{text: "A"} | _]
           } = call.(:stage)

    assert %{preset_id: ^b, revision: ^rev, melt: 33, hue: 44} = call.(:panel)
    stop_supervised!(Market)
    pid = start_supervised!({Market, opts})
    call = &Market.call(&1, pid)
    assert %{preset_id: ^b, live_preset_id: ^a, revision: ^rev} = call.(:panel)
    assert :ok = call.({:preset, a})

    assert %{
             dirty: false,
             melt: 75,
             hue: 66,
             brightness: 101,
             widgets: ["line1", "sd", "join"],
             gif: %{file: "/gifs/spooky/snow.gif"},
             layers: [%{text: "A", speed: 78} | _]
           } = call.(:panel)

    assert :ok = call.({:mode, "gif"})
    assert %{preset_id: "gif", melt: 10, hue: 20} = call.(:panel)
    assert :stale = call.({:take, rev})
    assert :ok = call.({:preset, b})
    assert :ok = call.({:take, call.(:panel).revision})

    assert %{
             preset_id: ^b,
             preset_name: "Holiday B",
             brightness: 202,
             melt: 33,
             hue: 44,
             widgets: ["sd", "line1"],
             layers: [%{text: "B"} | _]
           } = call.(:stage)

    assert :ok = call.({:fx, 14, 15})
    assert :ok = call.({:preset, a})
    assert :ok = call.({:live_fx, 91, 92})
    assert :ok = call.({:preset, b})
    assert %{melt: 14, hue: 15, dirty: true} = call.(:panel)
    assert %{melt: 91, hue: 92} = call.(:stage)
  end

  @tag :tmp_dir
  test "stack names remain unique, with failures leaving the selection and revision alone", %{
    tmp_dir: dir
  } do
    pid = start_supervised!({Market, path: Path.join(dir, "show"), tick: false})
    call = &Market.call(&1, pid)
    assert :ok = call.({:save_as, "Kréme"})
    before = call.(:panel)

    for name <- ["  ", String.duplicate("a", 49), "A\nB"] do
      assert :invalid_preset_name = call.({:save_as, name})
    end

    for name <- [" KRE\u0301ME ", "GIF", "dR. BeeF Supreme"] do
      assert :duplicate_preset_name = call.({:save_as, name})
    end

    assert :invalid = call.({:preset, "missing"})
    assert call.(:panel).revision == before.revision
    assert call.(:panel).preset_id == before.preset_id
    assert call.(:panel).presets == before.presets
    assert :ok = call.({:save_as, String.duplicate("É", 48)})
  end

  @tag :tmp_dir
  test "pre-library snapshots retain built-ins, edited templates and their distinct live scene",
       %{tmp_dir: dir} do
    path = Path.join(dir, "show")

    live =
      %Display{}
      |> Map.delete(:preset_id)
      |> Map.merge(%{mode: "crow", widgets: ["crow"], templates: %{}})

    draft = %{
      live
      | mode: "intro",
        widgets: ["intro", "santa"],
        templates: %{"crow" => %{widgets: ["crow", "line1"], melt: 27}}
    }

    legacy = %Market{display: live, draft: draft, revision: 71} |> Map.delete(:presets)
    File.write!(path, :erlang.term_to_binary(legacy))
    pid = start_supervised!({Market, path: path, tick: false})
    call = &Market.call(&1, pid)
    assert %{preset_id: "intro", live_preset_id: "crow", revision: 71} = call.(:panel)
    assert %{preset_name: "Dr. Crow", widgets: ["crow"]} = call.(:stage)
    assert :ok = call.({:preset, "crow"})
    assert %{widgets: ["crow", "line1"], melt: 27, dirty: true} = call.(:panel)
    assert :ok = call.({:preset, "intro"})
    assert call.(:panel).widgets == ["intro", "santa"]
  end
end
