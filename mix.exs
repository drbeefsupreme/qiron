defmodule Qiron.MixProject do
  use Mix.Project

  def project,
    do: [
      app: :qiron,
      version: "0.1.0",
      elixir: "~> 1.18",
      deps: [{:bandit, "~> 1.12"}, {:plug, "~> 1.16"}]
    ]

  def application, do: [extra_applications: [:logger, :crypto], mod: {Qiron.Application, []}]
end
