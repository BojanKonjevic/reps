export default {
  async fetch(req: Request): Promise<Response> {
    const url = new URL(req.url);
    if (url.pathname === "/snapshot") {
      return Response.json({
        note: "wire to R2 or D1 snapshot next",
        workouts: [],
        sets: [],
      });
    }
    const html =
      "<!doctype html><html><head><meta charset=utf-8><title>reps</title></head>" +
      "<body><h1>reps</h1><p>Snapshot viewer. Charts come next.</p>" +
      "<pre id=out>loading</pre>" +
      "<script>fetch('/snapshot').then(r=>r.json()).then(j=>{document.getElementById('out').textContent=JSON.stringify(j,null,2)})</script>" +
      "</body></html>";
    return new Response(html, { headers: { "content-type": "text/html" } });
  },
};
