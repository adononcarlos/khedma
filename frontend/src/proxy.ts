import { NextResponse, type NextRequest } from "next/server";

const locales = ["fr", "ar", "en"];

function preferredLocale(req: NextRequest) {
  const accept = req.headers.get("accept-language") ?? "";
  const first = accept.split(",")[0]?.slice(0, 2).toLowerCase();
  return locales.includes(first) ? first : "fr";
}

export function proxy(req: NextRequest) {
  const { pathname } = req.nextUrl;
  if (locales.some((l) => pathname === `/${l}` || pathname.startsWith(`/${l}/`))) return;
  req.nextUrl.pathname = `/${preferredLocale(req)}${pathname}`;
  return NextResponse.redirect(req.nextUrl);
}

export const config = { matcher: ["/((?!_next|api|favicon.ico|.*\\..*).*)"] };
