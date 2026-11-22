defmodule Qiron.Application do
  use Application

  def start(_, _) do
    children =
      if Application.fetch_env!(:qiron, :server) do
        [
          {Qiron.Market, path: System.get_env("SHOW_FILE", "data/show.etf"), name: Qiron.Market},
          Qiron.Panel,
          {Bandit,
           plug: Qiron.Web,
           port: String.to_integer(System.get_env("PORT", "4000")),
           ip: {0, 0, 0, 0}}
        ]
      else
        []
      end

    Supervisor.start_link(children, strategy: :one_for_one)
  end
end
