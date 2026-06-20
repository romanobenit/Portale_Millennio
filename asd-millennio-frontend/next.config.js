/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  output: "standalone",
  images: {
    remotePatterns: [
      { protocol: "https", hostname: "gateway.pinata.cloud" },
      { protocol: "https", hostname: "ipfs.io" },
    ],
  },
  async headers() {
    const isDev = process.env.NODE_ENV !== "production";
    return [
      {
        source: "/(.*)",
        headers: [
          { key: "X-Frame-Options", value: "DENY" },
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          // HSTS: solo in produzione (il browser cacherà la policy per 1 anno)
          ...(isDev
            ? []
            : [
                {
                  key: "Strict-Transport-Security",
                  value: "max-age=31536000; includeSubDomains; preload",
                },
              ]),
          {
            key: "Permissions-Policy",
            value: "camera=(), microphone=(), geolocation=(), payment=(self)",
          },
          {
            key: "Content-Security-Policy",
            value: [
              "default-src 'self'",
              // Keycloak per l'auth SSO
              // NOTA: la URL dell'API deve terminare con "/" per CSP prefix-match (W3C spec).
              // Senza trailing slash, CSP fa exact-match e blocca tutti i sottopath.
              `connect-src 'self' ${process.env.NEXT_PUBLIC_KEYCLOAK_URL || ""} ${(process.env.NEXT_PUBLIC_API_URL || "").replace(/\/?$/, "/")}`,
              "img-src 'self' data: https://gateway.pinata.cloud https://ipfs.io",
              // Stripe JS
              "script-src 'self' 'unsafe-inline' https://js.stripe.com",
              "frame-src https://js.stripe.com",
              "style-src 'self' 'unsafe-inline'",
              "font-src 'self'",
            ].join("; "),
          },
        ],
      },
    ];
  },
};

module.exports = nextConfig;
