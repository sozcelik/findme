"use client";

import { useEffect, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type Subscription = {
  plan: string;
  monthlyCreditsUsed: number;
  monthlyCreditsLimit: number;
  stripeCustomerId: string | null;
  stripeSubscriptionId: string | null;
};

const PLANS = [
  {
    id: "growth",
    name: "Growth",
    price: "$49/mo",
    credits: 50,
    features: ["50 pipeline runs/mo", "Unlimited content", "CMS publishing", "Social distribution"],
  },
  {
    id: "pro",
    name: "Pro",
    price: "$149/mo",
    credits: 200,
    features: ["200 pipeline runs/mo", "Everything in Growth", "Priority processing", "API access"],
  },
];

export default function BillingPage() {
  const [sub, setSub] = useState<Subscription | null>(null);
  const [loading, setLoading] = useState(true);
  const [redirecting, setRedirecting] = useState(false);

  useEffect(() => {
    fetch(`${API}/api/billing/subscription`)
      .then((r) => r.json())
      .then(setSub)
      .finally(() => setLoading(false));
  }, []);

  async function upgrade(priceKey: "growth" | "pro") {
    setRedirecting(true);
    const priceIdKey = priceKey === "growth" ? "NEXT_PUBLIC_STRIPE_GROWTH_PRICE_ID" : "NEXT_PUBLIC_STRIPE_PRO_PRICE_ID";
    const priceId = process.env[priceIdKey] ?? "";
    if (!priceId) {
      alert("Stripe not configured");
      setRedirecting(false);
      return;
    }
    const res = await fetch(`${API}/api/billing/create-checkout`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ priceId, userEmail: "" }),
    });
    if (!res.ok) {
      alert("Failed to create checkout session");
      setRedirecting(false);
      return;
    }
    const { url } = await res.json();
    window.location.href = url;
  }

  async function manageSubscription() {
    if (!sub?.stripeCustomerId) return;
    setRedirecting(true);
    const res = await fetch(`${API}/api/billing/portal`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ customerId: sub.stripeCustomerId }),
    });
    if (!res.ok) {
      alert("Failed to open billing portal");
      setRedirecting(false);
      return;
    }
    const { url } = await res.json();
    window.location.href = url;
  }

  if (loading) return <p className="text-sm text-muted-foreground">Loading...</p>;
  if (!sub) return <p className="text-sm text-destructive">Failed to load billing info.</p>;

  const usagePct = Math.min((sub.monthlyCreditsUsed / sub.monthlyCreditsLimit) * 100, 100);
  const isSubscribed = sub.plan !== "free" && sub.plan !== "starter";

  return (
    <div className="space-y-8">
      {/* Current Plan */}
      <section className="border border-border rounded-lg p-6">
        <h2 className="text-base font-medium mb-4">Current Plan</h2>
        <div className="flex items-center justify-between mb-4">
          <div>
            <span className="text-xl font-semibold capitalize">{sub.plan}</span>
            {isSubscribed && (
              <span className="ml-2 text-xs px-2 py-0.5 rounded-full bg-green-500/10 text-green-600">
                active
              </span>
            )}
          </div>
          {isSubscribed && sub.stripeCustomerId && (
            <button
              onClick={manageSubscription}
              disabled={redirecting}
              className="text-sm px-3 py-1.5 rounded-md border border-border hover:bg-muted disabled:opacity-50"
            >
              {redirecting ? "Redirecting..." : "Manage Subscription"}
            </button>
          )}
        </div>

        {/* Credit Usage */}
        <div>
          <div className="flex justify-between text-sm mb-1.5">
            <span className="text-muted-foreground">Pipeline runs this month</span>
            <span>
              {sub.monthlyCreditsUsed} / {sub.monthlyCreditsLimit}
            </span>
          </div>
          <div className="h-2 rounded-full bg-muted overflow-hidden">
            <div
              className={`h-full rounded-full transition-all ${
                usagePct >= 90 ? "bg-destructive" : "bg-primary"
              }`}
              style={{ width: `${usagePct}%` }}
            />
          </div>
          {usagePct >= 90 && (
            <p className="text-xs text-destructive mt-1">
              You are close to your limit. Upgrade to continue running pipelines.
            </p>
          )}
        </div>
      </section>

      {/* Plan Cards */}
      {!isSubscribed && (
        <section>
          <h2 className="text-base font-medium mb-4">Upgrade Your Plan</h2>
          <div className="grid grid-cols-2 gap-4">
            {PLANS.map((plan) => (
              <div key={plan.id} className="border border-border rounded-lg p-6 space-y-4">
                <div className="flex justify-between items-start">
                  <div>
                    <h3 className="font-semibold">{plan.name}</h3>
                    <p className="text-sm text-muted-foreground">{plan.credits} runs/mo</p>
                  </div>
                  <span className="text-lg font-bold">{plan.price}</span>
                </div>
                <ul className="space-y-1">
                  {plan.features.map((f) => (
                    <li key={f} className="text-sm text-muted-foreground flex items-center gap-2">
                      <span className="text-green-500">✓</span> {f}
                    </li>
                  ))}
                </ul>
                <button
                  onClick={() => upgrade(plan.id as "growth" | "pro")}
                  disabled={redirecting}
                  className="w-full text-sm px-4 py-2 rounded-md bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
                >
                  {redirecting ? "Redirecting..." : `Upgrade to ${plan.name}`}
                </button>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
