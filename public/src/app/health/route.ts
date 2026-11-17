export function GET() {
  // Liveness of Next itself; does not require DB access or backend secrets.
  return Response.json({ status: 'healthy' }, { headers: { 'Cache-Control': 'no-store' } });
}
