import { Link } from "react-router-dom";

const STEPS = [
  {
    title: "Define the role",
    body: "Write out up to three open positions \u2014 title, description, and the skills, experience, and education that matter.",
    icon: (
      <svg className="h-5 w-5 text-[#88AB80]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
      </svg>
    ),
  },
  {
    title: "Upload CVs",
    body: "Add up to ten candidate CVs as PDF or Word files for a single processing run.",
    icon: (
      <svg className="h-5 w-5 text-[#88AB80]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
      </svg>
    ),
  },
  {
    title: "Let the pipeline read them",
    body: "Each CV is parsed and compared against the role using retrieval-augmented evaluation, then scored against the requirements.",
    icon: (
      <svg className="h-5 w-5 text-[#88AB80]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M13 10V3L4 14h7v7l9-11h-7z" />
      </svg>
    ),
  },
  {
    title: "Review the judgment calls",
    body: "Clear fits and clear misses are sorted automatically. Anything in between is flagged for a person to decide.",
    icon: (
      <svg className="h-5 w-5 text-[#88AB80]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
  },
];

const ROLES = [
  { role: "Product", note: "Defines what \u201cgood fit\u201d means and keeps the review policy fair." },
  { role: "ML / Backend", note: "Builds the parsing, retrieval, and scoring pipeline behind the review." },
  { role: "Frontend", note: "Builds the workspace you're looking at \u2014 upload, review, and decide." },
];

export function HomePage() {
  return (
    <div className="relative min-h-screen bg-[#FDFBF7] text-stone-800">
      {/* Subtle Ambient Glow */}
      <div className="pointer-events-none fixed top-1/4 left-1/2 h-[900px] w-[900px] -translate-x-1/2 -translate-y-1/2 rounded-full bg-[#BCD9B4]/30 blur-[130px]" />

      <div className="relative z-10 mx-auto max-w-7xl px-9 py-16 sm:px-6">
        {/* Hero Section */}
        <div className="mx-auto max-w-2xl text-center">
          
          
          <h1 className="mt-5 font-sans text-4xl font-black tracking-tight text-stone-900 sm:text-6xl">
            HR AI <span className="text-[#5A8052]">Project</span>
          </h1>

         <p className="mt-5 text-base font-bold leading-relaxed text-stone-1000 sm:text-lg"> 
          An automated candidate screening platform leveraging language models and retrieval pipelines to parse resumes, match skill sets against role requirements, and streamline hiring decisions.
          </p>

          <div className="mt-8 flex flex-wrap justify-center gap-4">
            <Link
              to="/setup"
              className="group inline-flex items-center gap-2 rounded-xl bg-[#BCD9B4] px-6 py-3 text-sm font-bold text-emerald-950 shadow-sm transition-all duration-200 hover:bg-[#a8cd9f] hover:shadow-md focus:outline-none focus-visible:ring-2 focus-visible:ring-[#BCD9B4]"
            >
              Start a review
              <svg className="h-4 w-4 transition-transform group-hover:translate-x-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M14 5l7 7m0 0l-7 7m7-7H3" />
              </svg>
            </Link>

            <Link
              to="/cvs"
              className="inline-flex items-center rounded-xl border border-stone-200 bg-white/80 px-6 py-3 text-sm font-semibold text-stone-700 shadow-sm transition-all duration-200 hover:border-[#BCD9B4] hover:bg-stone-50 hover:text-stone-900 focus:outline-none focus-visible:ring-2 focus-visible:ring-[#BCD9B4]"
            >
              View all CVs
            </Link>
          </div>
        </div>

        {/* How it works */}
        <div className="mt-20">
          <div className="flex items-center gap-3">
            <h2 className="text-xs font-bold uppercase tracking-widest text-[#5A8052]">
              How it works
            </h2>
            <div className="h-[1px] flex-1 bg-stone-200" />
          </div>

          <ol className="mt-6 grid gap-4 sm:grid-cols-2">
            {STEPS.map((step, i) => (
              <li
                key={step.title}
                className="group relative overflow-hidden rounded-xl border border-stone-200/80 bg-white p-5 shadow-sm transition-all duration-300 hover:-translate-y-1.5 hover:scale-[1.02] hover:border-[#BCD9B4] hover:shadow-lg hover:shadow-[#BCD9B4]/20"
              >
                <div className="flex items-center justify-between">
                  <span className="flex h-9 w-9 items-center justify-center rounded-lg border border-[#BCD9B4]/60 bg-[#BCD9B4]/20 transition-transform duration-300 group-hover:scale-110">
                    {step.icon}
                  </span>
                  <span className="text-xs font-extrabold text-stone-400 group-hover:text-[#5A8052] transition-colors">
                    {String(i + 1).padStart(2, "0")}
                  </span>
                </div>

                <h3 className="mt-4 text-base font-bold text-stone-900 group-hover:text-[#415e3b] transition-colors">
                  {step.title}
                </h3>
                <p className="mt-1.5 text-xs leading-relaxed text-stone-600">
                  {step.body}
                </p>
              </li>
            ))}
          </ol>
        </div>

        {/* Who's behind it */}
        <div className="mt-20">
          <div className="flex items-center gap-3">
            <h2 className="text-xs font-bold uppercase tracking-widest text-[#5A8052]">
              Who's behind it
            </h2>
            <div className="h-[1px] flex-1 bg-stone-200" />
          </div>

          <p className="mt-4 text-sm text-stone-600 leading-relaxed">
            HR AI is built by LLMOps Team: Participants in the AI Infrastructure Operations Bootcamp by the Saudi Digital Academy and WeCloudData, specializing in containerization, cluster orchestration, and production AI deployment pipelines.         </p>

          <dl className="mt-6 grid gap-4 sm:grid-cols-3">
            {ROLES.map((r) => (
              <div
                key={r.role}
                className="rounded-xl border border-stone-200/80 bg-white p-5 shadow-sm transition-all duration-300 hover:border-[#BCD9B4]"
              >
                <dt className="text-sm font-bold text-stone-900 flex items-center gap-2">
                  <span className="h-2 w-2 rounded-full bg-[#BCD9B4]" />
                  {r.role}
                </dt>
                <dd className="mt-2 text-xs leading-relaxed text-stone-600">{r.note}</dd>
              </div>
            ))}
          </dl>
        </div>
      </div>
    </div>
  );
}