import { useEffect } from "react";
import { SignIn } from "@clerk/nextjs";

export default function Page() {
  useEffect(() => {
    if (typeof window === "undefined" || window.self === window.top) {
      return;
    }

    try {
      const currentHost = window.location.hostname;
      const hfDirectHost = "dpkmaurya2025-ai-healthcare-consultation-saas-dev.hf.space";

      if (
        (currentHost.includes("hf.space") || currentHost.includes("huggingface.co")) &&
        window.top &&
        window.top.location &&
        window.top.location.origin === window.location.origin
      ) {
        window.top.location.href = `https://${hfDirectHost}/sign-in`;
      }
    } catch {
      // Ignore cross-origin iframe redirects: HF embedding can block access to window.top.
    }
  }, []);

  return <SignIn routing="path" path="/sign-in" />;
}