export default {
  async fetch(request, env) {
    if (request.method === "OPTIONS") {
      return new Response(null, {
        status: 204,
        headers: {
          "Access-Control-Allow-Origin": "https://www.beehoantien.asia",
          "Access-Control-Allow-Credentials": "true",
          "Access-Control-Allow-Headers": "Content-Type, Authorization",
          "Access-Control-Allow-Methods": "GET, POST, PUT, PATCH, DELETE, OPTIONS",
          "Access-Control-Max-Age": "86400",
        },
      });
    }
    const origin = env.BACKEND_ORIGIN?.replace(/\/$/, "");
    if (!origin) {
      return new Response("BACKEND_ORIGIN is not configured", { status: 500 });
    }

    const url = new URL(request.url);
    const target = `${origin}${url.pathname}${url.search}`;
    const headers = new Headers(request.headers);
    headers.set("X-Forwarded-Host", url.host);
    headers.set("X-Forwarded-Proto", url.protocol.replace(":", ""));

    const response = await fetch(target, {
      method: request.method,
      headers,
      body: request.method === "GET" || request.method === "HEAD" ? undefined : request.body,
      redirect: "manual",
    });

    const output = new Response(response.body, response);
    output.headers.set("Access-Control-Allow-Origin", "https://www.beehoantien.asia");
    output.headers.set("Access-Control-Allow-Credentials", "true");
    output.headers.set("Access-Control-Allow-Headers", "Content-Type, Authorization");
    output.headers.set("Access-Control-Allow-Methods", "GET, POST, PUT, PATCH, DELETE, OPTIONS");
    return output;
  },
};
