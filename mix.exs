defmodule Qiron.MixProject do
  use Mix.Project

  def project,
    do: [
      app: :qiron,
      version: "0.1.0",
      elixir: "~> 1.18",
      releases: [qiron: [steps: [:assemble, &omit_build_cookie/1]]],
      deps: [{:bandit, "~> 1.12"}, {:plug, "~> 1.16"}]
    ]

  defp omit_build_cookie(release) do
    File.rm!(Path.join([release.path, "releases", "COOKIE"]))
    release
  end

  def application, do: [extra_applications: [:logger, :crypto], mod: {Qiron.Application, []}]
end
