import { Route, Routes } from "react-router-dom";
import { AppLayout } from "@/components/AppLayout";
import { HomePage } from "@/pages/HomePage";
import { SetupPage } from "@/pages/SetupPage";
import { ReviewWorkspacePage } from "@/pages/ReviewWorkspacePage";
import { AllCvsPage } from "@/pages/AllCvsPage";

export default function App() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route path="/" element={<HomePage />} />
        <Route path="/setup" element={<SetupPage />} />
        <Route path="/review" element={<ReviewWorkspacePage />} />
        <Route path="/cvs" element={<AllCvsPage />} />
        <Route path="*" element={<HomePage />} />
      </Route>
    </Routes>
  );
}
