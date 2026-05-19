import { FormEvent, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { BrainCircuit } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useToast } from "@/components/ui/toast";
import { useAuth } from "@/auth/useAuth";

export function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const auth = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const { toast } = useToast();

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setIsSubmitting(true);
    try {
      await auth.login({ email, password });
      const target = (location.state as { from?: { pathname?: string } } | null)?.from?.pathname || "/";
      navigate(target, { replace: true });
    } catch (error) {
      toast({ title: "Login failed", description: error instanceof Error ? error.message : "Check your credentials.", variant: "destructive" });
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="grid min-h-screen lg:grid-cols-[1.05fr_0.95fr]">
      <section className="hidden bg-primary p-10 text-primary-foreground lg:flex lg:flex-col lg:justify-between">
        <div className="flex items-center gap-3">
          <div className="rounded-md bg-primary-foreground/10 p-2">
            <BrainCircuit className="h-5 w-5" />
          </div>
          <span className="font-semibold">AI Recruiter ATS</span>
        </div>
        <div className="max-w-xl">
          <motion.h1 initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="text-5xl font-semibold leading-tight">
            Recruiter intelligence for resume-heavy hiring.
          </motion.h1>
          <p className="mt-5 text-lg text-primary-foreground/70">
            Parse, rank, explain, and move candidates through a polished ATS workflow powered by your AI backend.
          </p>
        </div>
      </section>
      <section className="flex items-center justify-center p-6">
        <Card className="w-full max-w-md">
          <CardHeader>
            <CardTitle>Welcome back</CardTitle>
            <CardDescription>Sign in to continue screening candidates.</CardDescription>
          </CardHeader>
          <CardContent>
            <form className="space-y-4" onSubmit={onSubmit}>
              <div className="space-y-2">
                <Label htmlFor="email">Email</Label>
                <Input id="email" type="email" value={email} onChange={(event) => setEmail(event.target.value)} required />
              </div>
              <div className="space-y-2">
                <Label htmlFor="password">Password</Label>
                <Input id="password" type="password" value={password} onChange={(event) => setPassword(event.target.value)} required />
              </div>
              <Button className="w-full" type="submit" disabled={isSubmitting}>
                {isSubmitting ? "Signing in..." : "Sign in"}
              </Button>
            </form>
            <p className="mt-5 text-center text-sm text-muted-foreground">
              New workspace?{" "}
              <Link className="font-medium text-foreground underline underline-offset-4" to="/register">
                Create an account
              </Link>
            </p>
          </CardContent>
        </Card>
      </section>
    </div>
  );
}
