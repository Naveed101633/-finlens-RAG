"use client";

import { Manrope, Space_Grotesk } from "next/font/google";
import { useEffect, useMemo, useState } from "react";

const bodyFont = Manrope({ subsets: ["latin"] });
const headingFont = Space_Grotesk({ subsets: ["latin"] });

type Citation = {
  page_number: number;
  source_file: string;
  chunk_id: string;
  score: number;
};

type QueryApiResponse = {
  answer: string;
  citations: Citation[];
  query: string;
  model_used: string;
};

type HealthApiResponse = {
  status: string;
  pipeline_info: Record<string, unknown>;
};

type UploadResponse = {
  filename: string;
  pages_loaded: number;
  chunks_created: number;
  status: string;
  message: string;
};

type UploadStartResponse = {
  job_id: string;
  status: string;
  message: string;
};

type UploadStatusResponse = {
  job_id: string;
  status: "queued" | "processing" | "completed" | "failed";
  stage?: string;
  filename?: string;
  pages_loaded?: number;
  chunks_created?: number;
  message?: string;
  error?: string;
};

type DocumentsResponse = {
  documents: string[];
  total: number;
};

const QUICK_QUESTIONS = [
  "What was the profit after tax?",
  "What are the main risks mentioned?"
] as const;

export default function Home() {
  const [question, setQuestion] = useState<string>("");
  const [result, setResult] = useState<QueryApiResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string>("");
  const [health, setHealth] = useState<HealthApiResponse | null>(null);
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const [uploadResult, setUploadResult] = useState<UploadResponse | null>(null);
  const [uploadError, setUploadError] = useState<string>("");
  const [uploadStage, setUploadStage] = useState<string>("");
  const [documents, setDocuments] = useState<string[]>([]);
  const [deletingDoc, setDeletingDoc] = useState<string | null>(null);
  const [showUpload, setShowUpload] = useState<boolean>(false);

  const apiBaseUrl = useMemo(() => {
    const rawBaseUrl = process.env.NEXT_PUBLIC_API_URL;
    const resolvedBaseUrl =
      rawBaseUrl && rawBaseUrl.trim().length > 0
        ? rawBaseUrl
        : "http://localhost:8000";

    // Prevent accidental double slashes in request URLs.
    return resolvedBaseUrl.replace(/\/+$/, "");
  }, []);

  useEffect(() => {
    const checkHealth = async () => {
      try {
        const response = await fetch(`${apiBaseUrl}/api/health`, {
          method: "GET",
        });
        if (!response.ok) {
          throw new Error("Health check failed");
        }
        const data: HealthApiResponse = await response.json();
        setHealth(data);
      } catch {
        setHealth({ status: "error", pipeline_info: {} });
      }
    };

    void checkHealth();
  }, [apiBaseUrl]);

  useEffect(() => {
    const fetchDocuments = async () => {
      try {
        const response = await fetch(`${apiBaseUrl}/api/documents`, {
          method: "GET",
        });

        if (!response.ok) {
          throw new Error("Unable to fetch indexed documents");
        }

        const data: DocumentsResponse = await response.json();
        setDocuments(data.documents);
      } catch {
        setDocuments([]);
      }
    };

    void fetchDocuments();
  }, [apiBaseUrl]);

  const submitQuery = async () => {
    if (!question.trim()) {
      setError("Please enter a question before analyzing.");
      return;
    }

    setIsLoading(true);
    setError("");

    try {
      const response = await fetch(`${apiBaseUrl}/api/query`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question: question.trim(),
          top_k: null,
        }),
      });

      if (!response.ok) {
        const detail = await response.text();
        throw new Error(detail || "Unable to process the query.");
      }

      const data: QueryApiResponse = await response.json();
      setResult(data);
    } catch (err) {
      const message =
        err instanceof Error
          ? err.message
          : "Something went wrong while contacting the API.";
      setError(message);
    } finally {
      setIsLoading(false);
    }
  };

  const uploadDocument = async () => {
    if (!uploadFile) {
      return;
    }

    setIsUploading(true);
    setUploadError("");
    setUploadResult(null);
    setUploadStage("Uploading file");

    try {
      const formData = new FormData();
      formData.append("file", uploadFile);

      const response = await fetch(`${apiBaseUrl}/api/upload`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const detail = await response.text();
        throw new Error(detail || "Failed to upload and index document.");
      }

      const startData: UploadStartResponse = await response.json();
      const timeoutAt = Date.now() + 20 * 60 * 1000;

      while (Date.now() < timeoutAt) {
        const statusResponse = await fetch(
          `${apiBaseUrl}/api/upload-status/${encodeURIComponent(startData.job_id)}`,
          { method: "GET" }
        );

        if (!statusResponse.ok) {
          throw new Error("Unable to fetch upload status.");
        }

        const statusData: UploadStatusResponse = await statusResponse.json();
        setUploadStage(statusData.stage ?? "Processing");

        if (statusData.status === "completed") {
          setUploadResult({
            filename: statusData.filename ?? uploadFile.name,
            pages_loaded: statusData.pages_loaded ?? 0,
            chunks_created: statusData.chunks_created ?? 0,
            status: "success",
            message: statusData.message ?? "Document uploaded and indexed successfully",
          });

          const docsResponse = await fetch(`${apiBaseUrl}/api/documents`, {
            method: "GET",
          });
          if (docsResponse.ok) {
            const docsData: DocumentsResponse = await docsResponse.json();
            setDocuments(docsData.documents);
          }
          setUploadStage("");
          return;
        }

        if (statusData.status === "failed") {
          throw new Error(statusData.error || "Upload processing failed.");
        }

        await new Promise((resolve) => {
          setTimeout(resolve, 1500);
        });
      }

      throw new Error("Upload is taking too long. Please try a smaller PDF or retry.");
    } catch (err) {
      const message =
        err instanceof TypeError
          ? "Network/CORS error: cannot reach backend upload endpoint. Check NEXT_PUBLIC_API_URL and backend CORS settings."
          : err instanceof Error
            ? err.message
            : "Something went wrong while uploading the document.";
      setUploadError(message);
      setUploadStage("");
    } finally {
      setIsUploading(false);
    }
  };

  const deleteDocument = async (filename: string) => {
    setDeletingDoc(filename);

    try {
      const response = await fetch(
        `${apiBaseUrl}/api/documents/${encodeURIComponent(filename)}`,
        {
          method: "DELETE",
        }
      );

      if (!response.ok) {
        const detail = await response.text();
        throw new Error(detail || "Failed to delete document.");
      }

      const docsResponse = await fetch(`${apiBaseUrl}/api/documents`, {
        method: "GET",
      });
      if (docsResponse.ok) {
        const docsData: DocumentsResponse = await docsResponse.json();
        setDocuments(docsData.documents);
      }
    } catch (err) {
      console.error("Failed to delete document:", err);
    } finally {
      setDeletingDoc(null);
    }
  };

  return (
    <div className={`${bodyFont.className} min-h-screen bg-slate-100 text-slate-900`}>
      <header className="bg-[#0f172a] text-white shadow-lg">
        <div className="mx-auto flex w-full max-w-6xl items-center justify-between px-6 py-5 sm:px-10">
          <div>
            <p className={`${headingFont.className} text-2xl font-bold tracking-tight`}>
              FinLens
            </p>
            <p className="mt-1 text-sm text-slate-300">
              AI-powered financial report analyst
            </p>
          </div>
          <div className="rounded-full border border-teal-500/40 bg-teal-500/10 px-4 py-1.5 text-xs font-semibold uppercase tracking-wide text-teal-200">
            API {health?.status === "ok" ? "Online" : "Checking"}
          </div>
        </div>
      </header>

      <section className="bg-[#0f172a] pb-14 pt-12 text-center text-white">
        <div className="mx-auto max-w-4xl px-6 sm:px-10">
          <h1 className={`${headingFont.className} text-3xl font-bold leading-tight sm:text-5xl`}>
            Ask Anything About Your Financial Documents
          </h1>
          <p className="mx-auto mt-4 max-w-2xl text-base text-slate-300 sm:text-lg">
            Upload any annual report - every answer is grounded in your document with source citations
          </p>
        </div>
      </section>

      <main className="-mt-8 pb-16">
        <div className="mx-auto w-full max-w-4xl px-6 sm:px-10">
          <section className="mb-6 rounded-2xl border border-slate-200 bg-white shadow-xl">
            <button
              type="button"
              onClick={() => setShowUpload((prev) => !prev)}
              className="flex w-full items-center justify-between px-6 py-4 text-left sm:px-8"
            >
              <span className={`${headingFont.className} text-lg font-semibold text-slate-900`}>
                Upload Financial Document
              </span>
              <svg
                className={`h-5 w-5 text-slate-600 transition-transform ${showUpload ? "rotate-180" : ""}`}
                viewBox="0 0 20 20"
                fill="none"
                xmlns="http://www.w3.org/2000/svg"
                aria-hidden="true"
              >
                <path d="M5 8L10 13L15 8" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </button>

            {showUpload ? (
              <div className="border-t border-slate-200 px-6 pb-6 pt-5 sm:px-8">
                <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-600">
                  Indexed Documents
                </h3>
                <div className="mt-3 flex flex-wrap gap-2">
                  {documents.length > 0 ? (
                    documents.map((doc) => (
                      <div
                        key={doc}
                        className="inline-flex items-center gap-2 rounded-full border border-teal-700/20 bg-teal-50 px-3 py-1 text-sm font-medium text-teal-800"
                      >
                        <span>{doc}</span>
                        <button
                          type="button"
                          onClick={() => deleteDocument(doc)}
                          disabled={deletingDoc === doc}
                          className="inline-flex h-[14px] w-[14px] items-center justify-center rounded-full bg-red-500 text-[10px] font-bold leading-none text-white transition hover:bg-red-600 disabled:cursor-not-allowed"
                          aria-label={`Delete ${doc}`}
                        >
                          {deletingDoc === doc ? (
                            <span className="h-[10px] w-[10px] animate-spin rounded-full border border-white/40 border-t-white" />
                          ) : (
                            "x"
                          )}
                        </button>
                      </div>
                    ))
                  ) : (
                    <p className="text-sm text-slate-500">No documents indexed yet</p>
                  )}
                </div>

                <div className="my-5 h-px w-full bg-slate-200" />

                <label
                  htmlFor="upload-pdf"
                  className="flex cursor-pointer items-center justify-center rounded-xl border-2 border-dashed border-slate-300 bg-slate-50 px-4 py-8 text-center text-sm font-medium text-slate-700 transition hover:border-[#0d9488] hover:bg-teal-50"
                >
                  {uploadFile ? uploadFile.name : "Click to select a PDF file"}
                </label>
                <input
                  id="upload-pdf"
                  type="file"
                  accept=".pdf"
                  className="hidden"
                  onChange={(e) => setUploadFile(e.target.files?.[0] ?? null)}
                />

                <div className="mt-4">
                  <button
                    type="button"
                    onClick={uploadDocument}
                    disabled={isUploading || !uploadFile}
                    className="inline-flex items-center justify-center gap-2 rounded-xl bg-[#0d9488] px-5 py-2.5 text-sm font-semibold text-white shadow-md transition hover:bg-[#0f766e] disabled:cursor-not-allowed disabled:opacity-70"
                  >
                    {isUploading ? (
                      <>
                        <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/40 border-t-white" />
                        {uploadStage ? uploadStage : "Uploading..."}
                      </>
                    ) : (
                      "Upload and Index"
                    )}
                  </button>
                </div>

                {uploadResult ? (
                  <div className="mt-4 rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
                    <p className="font-semibold">{uploadResult.filename}</p>
                    <p>Pages loaded: {uploadResult.pages_loaded}</p>
                    <p>Chunks created: {uploadResult.chunks_created}</p>
                  </div>
                ) : null}

                {uploadError ? (
                  <div className="mt-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                    {uploadError}
                  </div>
                ) : null}
              </div>
            ) : null}
          </section>

          <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-xl sm:p-8">
            <label
              htmlFor="question"
              className="mb-3 block text-sm font-semibold uppercase tracking-wide text-slate-600"
            >
              Your Question
            </label>
            <textarea
              id="question"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="e.g. What was the profit after tax? What are the main risks mentioned?"
              className="min-h-[160px] w-full resize-y rounded-xl border border-slate-300 bg-slate-50 p-4 text-base text-slate-900 shadow-sm outline-none transition focus:border-[#0d9488] focus:ring-2 focus:ring-[#0d9488]/30"
            />

            <div className="mt-5 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <button
                type="button"
                onClick={submitQuery}
                disabled={isLoading}
                className="inline-flex items-center justify-center gap-2 rounded-xl bg-[#0d9488] px-6 py-3 text-sm font-semibold text-white shadow-md transition hover:bg-[#0f766e] disabled:cursor-not-allowed disabled:opacity-70"
              >
                {isLoading ? (
                  <>
                    <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/40 border-t-white" />
                    Analyzing...
                  </>
                ) : (
                  "Analyze"
                )}
              </button>
              <p className="text-xs text-slate-500">Press Analyze to get a grounded answer</p>
              
            </div>

            <div className="mt-6 flex flex-wrap gap-2">
              {QUICK_QUESTIONS.map((quickQuestion) => (
                <button
                  key={quickQuestion}
                  type="button"
                  onClick={() => setQuestion(quickQuestion)}
                  className="rounded-full border border-teal-700/15 bg-teal-50 px-4 py-2 text-sm font-medium text-teal-800 transition hover:border-teal-700/40 hover:bg-teal-100"
                >
                  {quickQuestion}
                </button>
              ))}
            </div>

            {error ? (
              <div className="mt-5 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                {error}
              </div>
            ) : null}
          </div>

          {result ? (
            <section className="mt-8 rounded-2xl border border-slate-200 bg-white p-6 shadow-xl sm:p-8">
              <h2 className={`${headingFont.className} text-2xl font-semibold text-slate-900`}>
                Analysis Result
              </h2>

              <div className="mt-4 rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
                <p className="whitespace-pre-wrap leading-7 text-slate-800">{result.answer}</p>
              </div>

              <div className="mt-6">
                <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-600">
                  Citations
                </h3>
                <div className="mt-3 flex flex-wrap gap-2">
                  {result.citations.map((citation) => (
                    <div
                      key={`${citation.chunk_id}-${citation.page_number}`}
                      className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-slate-50 px-3 py-1.5 text-sm text-slate-700"
                    >
                      <span className="font-medium">
                        Page {citation.page_number} - {citation.source_file}
                      </span>
                      <span className="rounded-full bg-teal-100 px-2 py-0.5 text-xs font-semibold text-teal-800">
                        {citation.score.toFixed(3)}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              <p className="mt-6 text-xs text-slate-500">Model used: {result.model_used}</p>
            </section>
          ) : null}
          
        </div>
      </main>
      <footer className="bg-[#0f172a] py-6 text-center text-xs text-slate-400">
  Built with Hybrid RAG Pipeline • Semantic + Keyword Search • Gemini 2.5 Flash • Supports Any Financial Report
</footer>
    </div>
  );
}
