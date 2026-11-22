defmodule Qiron.ScreenCuesTest do
  use ExUnit.Case, async: true
  alias Qiron.Market

  @tag :tmp_dir
  test "live cues preserve the dirty draft, leave the snapshot alone, and expire", %{tmp_dir: dir} do
    path = Path.join(dir, "show")
    market = start_supervised!({Market, path: path, tick: false})
    call = &Market.call(&1, market)
    assert :ok = call.({:live_fx, 35, 64})
    assert :ok = call.({:mode, "intro"})
    assert %{dirty: true, revision: revision} = call.(:panel)
    original = File.stat!(path).inode
    assert :ok = call.({:screen_cue, "stars", 42})
    assert %{screen_cue: %{seed: 42}} = call.(:stage)
    assert :ok = call.({:screen_cue, "crack", 23})

    assert %{mode: "gif", melt: 35, hue: 64, screen_cue: %{kind: "crack", seed: 23}} =
             call.(:stage)

    assert %{dirty: true, mode: "intro", revision: ^revision, screen_cue: %{seed: 23}} =
             call.(:panel)

    Process.sleep(10_020)
    assert is_nil(call.(:stage).screen_cue)
    assert is_nil(call.(:panel).screen_cue)
    assert File.stat!(path).inode == original
  end

  @tag :tmp_dir
  test "restarting re-arms only the saved splice interval", %{tmp_dir: dir} do
    opts = [path: Path.join(dir, "show"), tick: false]
    pid = start_supervised!({Market, opts})
    call = &Market.call(&1, pid)
    assert :ok = call.({:splice_seconds, 60})
    assert :ok = call.({:screen_cue, "stars", 4})
    Process.sleep(150)
    generation = call.(:stage).splice_generation
    before_restart = call.(:stage).splice_elapsed_ms
    assert before_restart >= 150
    assert :ok = call.({:splice_seconds, 60})
    assert call.(:stage).splice_elapsed_ms >= before_restart
    assert call.(:panel).splice_generation == generation
    stop_supervised!(Market)
    pid = start_supervised!({Market, opts})

    assert %{splice_seconds: 60, screen_cue: nil, splice_elapsed_ms: elapsed} =
             Market.call(:stage, pid)

    assert elapsed < before_restart
    assert Market.call(:panel, pid).splice_generation != generation
    assert :ok = Market.call({:splice_seconds, 0}, pid)
    assert %{splice_seconds: 0, splice_elapsed_ms: 0} = Market.call(:panel, pid)
  end
end
