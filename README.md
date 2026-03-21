
---
title: AI Healthcare Consultation SaaS
emoji: 🏥
colorFrom: blue
colorTo: green
sdk: docker
app_port: 7860
pinned: false
---

This is a [Next.js](https://nextjs.org) project bootstrapped with [`create-next-app`](https://nextjs.org/docs/pages/api-reference/create-next-app).

## Getting Started

First, run the development server:

```bash
npm run dev
# or
yarn dev
# or
pnpm dev
# or
bun dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

You can start editing the page by modifying `pages/index.tsx`. The page auto-updates as you edit the file.

[API routes](https://nextjs.org/docs/pages/building-your-application/routing/api-routes) can be accessed on [http://localhost:3000/api/hello](http://localhost:3000/api/hello). This endpoint can be edited in `pages/api/hello.ts`.

The `pages/api` directory is mapped to `/api/*`. Files in this directory are treated as [API routes](https://nextjs.org/docs/pages/building-your-application/routing/api-routes) instead of React pages.

This project uses [`next/font`](https://nextjs.org/docs/pages/building-your-application/optimizing/fonts) to automatically optimize and load [Geist](https://vercel.com/font), a new font family for Vercel.

## Learn More

To learn more about Next.js, take a look at the following resources:

- [Next.js Documentation](https://nextjs.org/docs) - learn about Next.js features and API.
- [Learn Next.js](https://nextjs.org/learn-pages-router) - an interactive Next.js tutorial.

You can check out [the Next.js GitHub repository](https://github.com/vercel/next.js) - your feedback and contributions are welcome!

## Deploy on Vercel

The easiest way to deploy your Next.js app is to use the [Vercel Platform](https://vercel.com/new?utm_medium=default-template&filter=next.js&utm_source=create-next-app&utm_campaign=create-next-app-readme) from the creators of Next.js.

Check out our [Next.js deployment documentation](https://nextjs.org/docs/pages/building-your-application/deploying) for more details.

*******************************************************************
🚀 AI Parenting Idea SaaS

An AI-powered subscription-based SaaS application that generates innovative parenting ideas using OpenAI, built with a modern full-stack architecture.

🧠 Overview

AI Parenting Idea SaaS is a full-stack web application that:

Authenticates users with Clerk

Handles subscriptions & billing

Protects premium features

Streams AI-generated content in real-time

Uses OpenAI to generate creative parenting ideas

This project demonstrates production-ready SaaS architecture with authentication, payments, and AI integration.

🏗️ Tech Stack
🔹 Frontend

Next.js (App Router)

TypeScript

Tailwind CSS

React Markdown

Server-Sent Events (Streaming)

🔹 Backend

FastAPI

OpenAI API (Streaming)

JWT Verification (Clerk)

Server-Sent Events (SSE)

🔹 Authentication & Billing

Clerk (Authentication & User Management)

Stripe (Subscription Billing)

JWT & JWKS-based token verification

🔹 Deployment

Vercel (Frontend + API)

GitHub (Version Control)

🔐 Authentication Flow

User signs in using Clerk.

Clerk issues a JWT token.

Frontend sends JWT in Authorization header.

Backend verifies JWT using Clerk JWKS.

Access granted only to subscribed users.

💳 Subscription & Feature Gating

Premium subscription required to access idea generation.

Clerk Billing manages subscription lifecycle.

<Protect> component gates premium content.

Backend validates subscription before generating AI response.

⚡ Real-Time AI Streaming

The app uses:

OpenAI streaming responses

FastAPI StreamingResponse

Server-Sent Events (SSE)

fetch-event-source on frontend

This enables real-time idea generation similar to ChatGPT-style streaming.

📂 Project Structure
saap/
 ├── pages/
 │    ├── index.tsx        # Landing page
 │    ├── product.tsx      # Premium feature page
 │    ├── _app.tsx         # Clerk Provider
 │    └── _document.tsx    # HTML skeleton
 ├── api/
 │    └── index.py         # FastAPI streaming backend
 ├── styles/
 │    └── globals.css
 ├── README.md
 └── package.json
🛠️ Environment Variables

The following environment variables are required:

NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=
CLERK_SECRET_KEY=
CLERK_JWKS_URL=
OPENAI_API_KEY=

⚠️ Never commit .env files to GitHub.

🚀 Local Development
npm install
vercel dev
🌍 Production Deployment
vercel --prod
📸 Demo

Add your live Vercel URL here:

https://your-vercel-app-url.vercel.app
🧩 Key Features

🔐 Secure JWT-based authentication

💳 Subscription-based feature access

⚡ Real-time AI streaming

🎨 Clean UI with Tailwind Typography

🛡️ Backend subscription enforcement

☁️ Cloud deployment with Vercel

📈 Future Improvements

Usage-based billing (token limits)

Admin dashboard

Idea history storage

User analytics

Multi-model support

👨‍💻 Author

Deepak Maurya
AI/ML Engineer | GenAI Enthusiast