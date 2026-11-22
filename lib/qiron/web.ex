defmodule Qiron.Web do
  use Plug.Router
  alias Qiron.Market

  plug(:headers)

  plug(Plug.Static,
    at: "/",
    from: {:qiron, "priv/static"},
    only:
      ~w(style.css compositor.css stage.css screen-cues.js splice-jfk.png splice-911.png mixer.js compositor.js exchange.css app.js booth.js stage.js telethon.gif dr-crow.gif dr-beef.gif peter-thiel.gif santa.gif archivo-black.ttf barlow-condensed.ttf)
  )

  plug(:match)
  plug(:authorize)
  plug(Plug.Parsers, parsers: [:json], json_decoder: JSON, length: 205_000)
  plug(:dispatch)

  get("/", do: page(conn, "audience"))
  get("/stage", do: page(conn, "stage"))
  get("/operator", do: page(conn, "operator"))
  get("/api/stage", do: respond(conn, Market.call(:stage)))

  get "/api/panel" do
    respond(conn, Qiron.Panel.status())
  end

  get "/api/me" do
    {conn, id} = seat(conn)
    respond(conn, Market.call({:account, id}))
  end

  post "/api/trade" do
    {conn, id} = seat(conn)

    respond(
      conn,
      Market.call(
        {:trade, id, conn.body_params["side"], Map.get(conn.body_params, "leverage", 1)}
      )
    )
  end

  post "/api/refill" do
    {conn, id} = seat(conn)
    respond(conn, Market.call({:refill, id}))
  end

  post "/api/operator" do
    command =
      case conn.body_params do
        %{"preset" => id} when is_binary(id) ->
          {:preset, id}

        %{"save_as" => name} when is_binary(name) ->
          {:save_as, name}

        %{"hold" => held} ->
          {:hold, held}

        %{"volatility_bps" => value} when value in 0..500 ->
          {:volatility_bps, value}

        %{"nudge" => dir} ->
          {:nudge, dir}

        %{"mark" => mark} when is_number(mark) and mark >= 1 and mark <= 10_000 ->
          {:mark, round(mark * 100)}

        %{"mode" => mode} ->
          {:mode, mode}

        %{"take" => revision} when is_integer(revision) ->
          {:take, revision}

        %{"gif" => %{"preset" => preset, "file" => file}} ->
          {:gif, preset, file}

        %{"live_fx" => %{"melt" => melt, "hue" => hue}} when melt in 0..100 and hue in 0..100 ->
          {:live_fx, melt, hue}

        %{"widgets" => widgets} ->
          {:widgets, widgets}

        %{"melt" => melt, "hue" => hue} ->
          {:fx, melt, hue}

        %{"melt" => melt} ->
          {:melt, melt}

        %{"hue" => hue} ->
          {:hue, hue}

        %{"screen_cue" => kind} when kind in ["crack", "stars"] ->
          {:screen_cue, kind}

        %{"splice_seconds" => seconds} when seconds in [0, 5, 60] ->
          {:splice_seconds, seconds}

        %{"brightness" => value} ->
          {:brightness, value}

        %{"layer" => i, "speed" => speed} ->
          {:speed, i, speed}

        %{"action" => name} ->
          {:action, name}

        %{"layer" => i, "text" => t} ->
          {:line, i, t}

        _ ->
          :invalid
      end

    result =
      case command do
        {kind, _} when kind in [:mark, :nudge, :hold, :volatility_bps] -> Market.call(command)
        :invalid -> :invalid
        other -> Qiron.Panel.command(other)
      end

    respond(conn, result)
  end

  match(_, do: send_resp(conn, 404, "Page not found"))

  defp headers(conn, _) do
    conn
    |> put_resp_header("cache-control", "no-store")
    |> put_resp_header("x-content-type-options", "nosniff")
    |> put_resp_header("referrer-policy", "same-origin")
    |> put_resp_header(
      "content-security-policy",
      "default-src 'self'; script-src 'self'; style-src 'self'; frame-ancestors 'none'; base-uri 'none'"
    )
  end

  defp authorize(conn, _) do
    cond do
      conn.method == "POST" and get_req_header(conn, "x-qiron") != ["1"] ->
        conn |> send_resp(403, "Forbidden") |> halt()

      Plug.Router.match_path(conn) in ["/operator", "/api/operator", "/api/panel"] ->
        password = System.get_env("OPERATOR_PASSWORD", "")

        if String.length(password) >= 3 do
          Plug.BasicAuth.basic_auth(conn, username: "beef", password: password)
        else
          conn
          |> send_resp(503, "Set OPERATOR_PASSWORD to at least 3 characters to enable the booth.")
          |> halt()
        end

      true ->
        conn
    end
  end

  defp seat(conn) do
    conn = fetch_cookies(conn)

    case conn.req_cookies["qiron_seat"] do
      id when is_binary(id) and byte_size(id) == 32 ->
        {conn, id}

      _ ->
        id = Base.url_encode64(:crypto.strong_rand_bytes(24), padding: false)

        {put_resp_cookie(conn, "qiron_seat", id,
           http_only: true,
           same_site: "Strict",
           secure: System.get_env("COOKIE_SECURE") == "true",
           max_age: 604_800
         ), id}
    end
  end

  defp respond(conn, :wrong_mode),
    do: send_resp(conn, 409, "Add the corresponding widget to use this control.")

  defp respond(conn, :stale),
    do: send_resp(conn, 409, "Draft changed. Refresh before taking live.")

  defp respond(conn, :not_ready), do: send_resp(conn, 409, "Draft is not ready on the panel.")

  defp respond(conn, :liquidated),
    do: send_resp(conn, 409, "Claim your next slug when the cooldown ends.")

  defp respond(conn, :offline),
    do: send_resp(conn, 503, "Panel disconnected or acknowledgment timed out")

  defp respond(conn, :rejected), do: send_resp(conn, 502, "Panel rejected command")

  defp respond(conn, :invalid_preset_name),
    do: send_resp(conn, 422, "Use a stack name of 1 to 48 characters on one line.")

  defp respond(conn, :duplicate_preset_name),
    do: send_resp(conn, 422, "A saved stack already has that name.")

  defp respond(conn, :invalid), do: send_resp(conn, 422, "Invalid command")
  defp respond(conn, :ok), do: respond(conn, %{ok: true})

  defp respond(conn, data),
    do: conn |> put_resp_content_type("application/json") |> send_resp(200, JSON.encode!(data))

  defp page(conn, name),
    do:
      conn
      |> put_resp_content_type("text/html")
      |> send_file(200, Application.app_dir(:qiron, "priv/static/#{name}.html"))
end
