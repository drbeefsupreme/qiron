defmodule Qiron.PnlHistory do
  @runs_kept 24
  @points_kept 192

  def start(prior, at, pnl) do
    id =
      case prior do
        [] -> 1
        [latest | _] -> latest.id + 1
      end

    [
      %{id: id, started_at_ms: at, ended_at_ms: nil, points: [[at, pnl]]}
      | Enum.take(prior, @runs_kept - 1)
    ]
  end

  def sample([run | older] = history, at, pnl) do
    [[previous_at, previous_pnl] | rest] = run.points
    at = max(at, previous_at)

    cond do
      previous_pnl == pnl and previous_at == at ->
        history

      previous_pnl == pnl and match?([[_, ^pnl] | _], rest) ->
        [%{run | points: [[at, pnl] | rest]} | older]

      true ->
        [%{run | points: compact([[at, pnl] | run.points])} | older]
    end
  end

  def finish(history, at, pnl) do
    [run | older] = sample(history, at, pnl)
    [[ended, _] | _] = run.points
    [%{run | ended_at_ms: ended} | older]
  end

  defp compact(points) when length(points) <= @points_kept, do: points

  defp compact([latest | earlier]) do
    [first | middle] = Enum.reverse(earlier)

    retained =
      middle
      |> Enum.chunk_every(4)
      |> Enum.flat_map(fn group ->
        {low, high} = Enum.min_max_by(group, &List.last/1)
        Enum.filter(group, &(&1 == low or &1 == high)) |> Enum.uniq()
      end)

    [latest | Enum.reverse([first | retained])]
  end

  def public(runs) do
    for run <- Enum.reverse(runs) do
      points = for [at, cents] <- Enum.reverse(run.points), do: [at, json_cents(cents)]
      %{run | points: points}
    end
  end

  defp json_cents(cents) when abs(cents) > 9_007_199_254_740_991, do: Integer.to_string(cents)
  defp json_cents(cents), do: cents
end
