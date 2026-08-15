import { ClerkProvider } from '@clerk/nextjs';
import type { AppProps } from 'next/app';
import 'react-datepicker/dist/react-datepicker.css';
import '../styles/globals.css';

export default function MyApp({ Component, pageProps }: AppProps) {
  return (
    <ClerkProvider
      publishableKey={process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY}
      afterSignInUrl="/product"
      afterSignUpUrl="/product"
      afterSignOutUrl="/"
      signInFallbackRedirectUrl="/product"
      signUpFallbackRedirectUrl="/product"
      signInForceRedirectUrl="/product"
      signUpForceRedirectUrl="/product"
    >
      <Component {...pageProps} />
    </ClerkProvider>
  );
}