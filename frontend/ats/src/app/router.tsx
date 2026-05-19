import { createBrowserRouter } from "react-router-dom";
import { AppShell } from "@/components/layout/AppShell";
import { RequireAuth } from "@/auth/RequireAuth";
import { DashboardPage } from "@/pages/DashboardPage";
import { LoginPage } from "@/pages/LoginPage";
import { RegisterPage } from "@/pages/RegisterPage";
import { JobsPage } from "@/pages/JobsPage";
import { UploadPage } from "@/pages/UploadPage";
import { CandidatesPage } from "@/pages/CandidatesPage";
import { CandidateProfilePage } from "@/pages/CandidateProfilePage";
import { PipelinePage } from "@/pages/PipelinePage";
import { SettingsPage } from "@/pages/SettingsPage";

export const router = createBrowserRouter([
  { path: "/login", element: <LoginPage /> },
  { path: "/register", element: <RegisterPage /> },
  {
    element: <RequireAuth />,
    children: [
      {
        element: <AppShell />,
        children: [
          { index: true, element: <DashboardPage /> },
          { path: "jobs", element: <JobsPage /> },
          { path: "uploads", element: <UploadPage /> },
          { path: "candidates", element: <CandidatesPage /> },
          { path: "candidates/:id", element: <CandidateProfilePage /> },
          { path: "pipeline", element: <PipelinePage /> },
          { path: "settings", element: <SettingsPage /> },
        ],
      },
    ],
  },
]);
