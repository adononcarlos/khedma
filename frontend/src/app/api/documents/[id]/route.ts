import { authFetch } from "@/lib/session";

// Téléchargement des PDF générés : le jeton reste côté serveur (cookie httpOnly).
export async function GET(_: Request, ctx: RouteContext<"/api/documents/[id]">) {
  const { id } = await ctx.params;
  if (!/^\d+$/.test(id)) return new Response("Not found", { status: 404 });
  const r = await authFetch(`/api/me/documents/${id}.pdf`);
  if (!r.ok) return new Response("Not found", { status: r.status });
  return new Response(r.body, {
    headers: { "content-type": "application/pdf", "content-disposition": r.headers.get("content-disposition") ?? "attachment" },
  });
}
