import { NextRequest, NextResponse } from "next/server";
import { getServerSession } from "next-auth/next";
import { authOptions } from "@/lib/auth";

export async function POST(request: NextRequest) {
  const session = await getServerSession(authOptions);
  if (!session) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const body = await request.json();
  const { action, token } = body;

  if (action === "test") {
    if (!token) {
      return NextResponse.json(
        { success: false, error: "Token is required" },
        { status: 400 }
      );
    }
    try {
      const res = await fetch(
        "https://api.hubapi.com/crm/v3/objects/contacts?limit=1",
        { headers: { Authorization: `Bearer ${token}` } }
      );
      if (res.ok) {
        return NextResponse.json({ success: true });
      }
      return NextResponse.json({
        success: false,
        error: `HubSpot returned ${res.status}`,
      });
    } catch {
      return NextResponse.json({
        success: false,
        error: "Failed to reach HubSpot API",
      });
    }
  }

  if (action === "sync") {
    // Stub — sync engine integration is a future step
    return NextResponse.json({
      success: true,
      counts: { contacts: 0, companies: 0, deals: 0, tickets: 0 },
      message:
        "Sync endpoint ready. Connect the sync engine to enable full sync.",
    });
  }

  return NextResponse.json({ error: "Invalid action" }, { status: 400 });
}
