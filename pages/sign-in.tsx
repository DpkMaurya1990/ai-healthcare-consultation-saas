import { useEffect } from "react";
import { SignIn } from "@clerk/nextjs";

export default function Page() {
  useEffect(() => {
    // Agar page iframe ke andar open hua hai (jaise Hugging Face Spaces embed UI)
    if (typeof window !== "undefined" && window.self !== window.top) {
      const hfDirectHost = "dpkmaurya2025-ai-healthcare-consultation-saas-dev.hf.space";
      // Agar current hostname hf.space direct domain nahi hai ya iframe mein trap hai
      if (window.location.hostname.includes("hf.space") || window.location.hostname.includes("huggingface.co")) {
        window.top.location.href = `https://${hfDirectHost}/sign-in`;
      }
    }
  }, []);

  return <SignIn routing="path" path="/sign-in" />;
}