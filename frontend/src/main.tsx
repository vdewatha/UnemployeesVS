import { createRoot } from "react-dom/client";
import "./index.css";
import App from "./App.tsx";
import { StreamProvider } from "./providers/Stream.tsx";
import { ThreadProvider } from "./providers/Thread.tsx";
import { QueryParamProvider } from "use-query-params";
import { ReactRouter6Adapter } from "use-query-params/adapters/react-router-6";
import { BrowserRouter } from "react-router-dom";
import { Toaster } from "@/components/ui/sonner";

createRoot(document.getElementById("root")!).render(
  <BrowserRouter>
    <QueryParamProvider adapter={ReactRouter6Adapter}>
      <ThreadProvider>
        <StreamProvider>
          <App />
        </StreamProvider>
      </ThreadProvider>
    </QueryParamProvider>
    <Toaster />
  </BrowserRouter>,
);
