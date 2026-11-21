defmodule Qiron.Web do
  use Plug.Router
  alias Qiron.Market

  plug(:headers)

  plug(Plug.Static,
    at: "/",
    from: {:qiron, "priv/static"},
    only: ~w(style.css app.js specimen.js)
  )

  plug(:match)
  plug(:authorize)
  plug(Plug.Parsers, parsers: [:json], json_decoder: JSON, length: 2048)
  plug(:dispatch)

  get("/", do: page(conn, "audience"))
  get("/stage", do: page(conn, "stage"))
  get("/operator", do: page(conn, "operator"))
  get("/api/stage", do: respond(conn, Market.call(:stage)))

  get "/api/me" do
    {conn, id} = seat(conn)
    respond(conn, Market.call({:account, id}))
  end

  post "/api/trade" do
    {conn, id} = seat(conn)
    respond(conn, Market.call({:trade, id, conn.body_params["side"]}))
  end

  post "/api/operator" do
    command =
      case conn.body_params do
        %{"hold" => held} ->
          {:hold, held}

        %{"nudge" => dir} ->
          {:nudge, dir}

        %{"mark" => mark} when is_number(mark) and mark >= 1 and mark <= 10_000 ->
          {:mark, round(mark * 100)}

        %{"layer" => i, "text" => t} ->
          {:line, i, t}

        _ ->
          :invalid
      end

    respond(conn, Market.call(command))
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

      Plug.Router.match_path(conn) in ["/operator", "/api/operator"] ->
        case System.get_env("OPERATOR_PASSWORD") do
          pw when is_binary(pw) and byte_size(pw) >= 12 ->
            Plug.BasicAuth.basic_auth(conn, username: "beef", password: pw)

          _ ->
            conn
            |> send_resp(
              503,
              "Set OPERATOR_PASSWORD to at least 12 characters to enable the booth."
            )
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
