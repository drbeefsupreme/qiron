defmodule Qiron.WidgetScenesTest do
  use ExUnit.Case, async: true
  alias Qiron.Market

  @tag :tmp_dir
  test "stacks, effects and widget content belong to each scene", %{tmp_dir: dir} do
    path = Path.join(dir, "show")
    opts = [path: path, tick: false]
    pid = start_supervised!({Market, opts})
    call = &Market.call(&1, pid)
    assert call.(:stage).widgets == ~w(sd line1 line2 line3 line4 line5 lineF)
    assert :ok = call.({:mode, "blood"})
    assert call.(:panel).widgets == ["chart", "price", "interest"]
    assert :invalid = call.({:widgets, ["chart", "chart"]})
    assert :invalid = call.({:widgets, ["alien"]})
    assert :invalid = call.({:fx, 101, 0})

    widgets = ~w(peter sd lineF ticker santa callin)
    assert :ok = call.({:widgets, widgets})
    assert :ok = call.({:line, 6, "MERRY"})
    assert :ok = call.({:speed, 6, 78})
    assert :ok = call.({:gif, "gifS", "/gifs/spooky/eve.gif"})
    assert :wrong_mode = call.({:line, 1, "HIDDEN"})
    assert :ok = call.({:fx, 8, 37})
    assert :ok = call.({:take, call.(:panel).revision})
    assert %{widgets: ^widgets, melt: 8, hue: 37} = live = call.(:stage)
    assert %{id: 6, text: "MERRY", speed: 78} = List.last(live.layers)
    assert :ok = call.({:mode, "intro"})
    assert call.(:panel).widgets == ["intro"]
    assert :ok = call.({:widgets, []})
    assert :ok = call.({:melt, 54})
    assert :ok = call.({:hue, 3})
    revision = call.(:panel).revision
    assert :ok = call.({:live_fx, 90, 100})
    assert %{widgets: ^widgets, melt: 90, hue: 100} = call.(:stage)
    assert %{widgets: [], melt: 54, hue: 3, dirty: true, revision: ^revision} = call.(:panel)

    stop_supervised!(Market)
    pid = start_supervised!({Market, opts})
    call = &Market.call(&1, pid)
    assert %{live_melt: 90, live_hue: 100, melt: 54} = call.(:panel)
    assert :ok = call.({:take, revision})
    assert %{widgets: [], mode: "intro"} = call.(:stage)
    assert :ok = call.({:live_fx, 13, 27})
    assert %{melt: 13, hue: 27, live_hue: 27, dirty: false} = call.(:panel)
    assert :ok = call.({:mode, "blood"})

    assert %{widgets: ^widgets, melt: 90, hue: 100, gif: %{file: "/gifs/spooky/eve.gif"}} =
             call.(:panel)

    assert :ok = call.({:mode, "intro"})
    assert %{widgets: [], melt: 13, hue: 27, dirty: false} = call.(:panel)
  end

  @tag :tmp_dir
  test "legacy portrait snapshots retain their GIF template", %{tmp_dir: dir} do
    path = Path.join(dir, "show")

    old = %{
      __struct__: Qiron.Display,
      mode: "crow",
      brightness: 43,
      gif: %{preset: "gifJ", file: "/gifs/joker/open.gif", playing: true},
      lines: %{1 => "TELETHON"},
      speeds: %{}
    }

    File.write!(path, :erlang.term_to_binary(%Market{display: old, draft: old}))
    pid = start_supervised!({Market, path: path, tick: false})
    assert %{mode: "crow", widgets: ["crow"], brightness: 43} = Market.call(:stage, pid)
    assert :ok = Market.call({:mode, "gif"}, pid)

    assert %{gif: %{file: "/gifs/joker/open.gif"}, layers: [%{text: "TELETHON"} | _]} =
             Market.call(:panel, pid)
  end
end
