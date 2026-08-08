"use client"

import { useState, FormEvent } from 'react';
import { useAuth } from '@clerk/nextjs';
import DatePicker from 'react-datepicker';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkBreaks from 'remark-breaks';
import { fetchEventSource } from '@microsoft/fetch-event-source';
import { UserButton } from '@clerk/nextjs';

type ConsultationStreamError = Error & {
    status?: number;
    requestId?: string;
};

function buildConsultationError(message: string, status?: number, requestId?: string): ConsultationStreamError {
    const error = new Error(message) as ConsultationStreamError;
    if (status !== undefined) {
        error.status = status;
    }
    if (requestId) {
        error.requestId = requestId;
    }
    return error;
}

function ConsultationForm() {
    const { getToken } = useAuth();

    // Form state
    const [patientName, setPatientName] = useState('');
    const [senderName, setSenderName] = useState('Dr. Sharma Clinic');
    const [visitDate, setVisitDate] = useState<Date | null>(new Date());
    const [notes, setNotes] = useState('');
    const [patientEmail, setPatientEmail] = useState('');
    const [patientPhone, setPatientPhone] = useState('');

    // Streaming state
    const [output, setOutput] = useState('');
    const [loading, setLoading] = useState(false);
    const [copied, setCopied] = useState(false);
    const [errorMessage, setErrorMessage] = useState('');
    const [requestId, setRequestId] = useState('');

    function normalizeGreetingForDisplay(text: string, name: string): string {
        const normalizedName = name.trim();
        const greeting = normalizedName ? `Hello ${normalizedName},` : 'Hello,';
        const marker = /###\s*Draft of email to patient[^\n]*\n/i;
        const match = text.match(marker);
        const greetingPattern = /^(\s*)(Dear(?:\s+[^,\n]+)?\s*,?|Hello(?:\s+[^,\n]+)?\s*,?|Hi(?:\s+[^,\n]+)?\s*,?)/im;

        if (match && match.index !== undefined) {
            const before = text.slice(0, match.index + match[0].length);
            const after = text.slice(match.index + match[0].length);
            const normalizedAfter = after.replace(greetingPattern, `${greeting}`);
            return before + normalizedAfter;
        }

        return text.replace(greetingPattern, greeting);
    }

    function extractPatientEmail(fullOutput: string): { subject: string; body: string } {
        const normalizedOutput = normalizeGreetingForDisplay(fullOutput, patientName);
        const subjectMatch = normalizedOutput.match(/(?:^|\n)Subject:\s*(.+)\n/i);
        const marker = /###\s*Draft of email to patient[^\n]*\n/i;
        const match = normalizedOutput.match(marker);
        const defaultSubject = 'Follow-up from your recent visit';

        let body = normalizedOutput;
        if (match && match.index !== undefined) {
            body = normalizedOutput.slice(match.index + match[0].length).trim();
        }

        body = body.replace(/^Subject:\s*.+\n/i, '').trim();

        return {
            subject: subjectMatch?.[1]?.trim() || defaultSubject,
            body,
        };
    }

    function buildEmailPreviewMarkdown() {
        const { subject, body } = extractPatientEmail(output);
        if (!body) {
            return '';
        }

        return `Subject: ${subject}\n\n${body}`;
    }

    function buildGmailUrl() {
        const { subject, body } = extractPatientEmail(output);
        const params = new URLSearchParams();
        if (patientEmail.trim()) {
            params.set('to', patientEmail.trim());
        }
        params.set('su', subject);
        params.set('body', body);
        return `https://mail.google.com/mail/?view=cm&fs=1&${params.toString()}`;
    }

    function buildWhatsAppUrl() {
        const { body } = extractPatientEmail(output);
        const digitsOnly = patientPhone.replace(/[^\d]/g, '');
        const encodedText = encodeURIComponent(body);
        return `https://wa.me/${digitsOnly}?text=${encodedText}`;
    }

    async function handleCopy() {
        try {
            const { subject, body } = extractPatientEmail(output);
            const textToCopy = `Subject: ${subject}\n\n${body}`;
            await navigator.clipboard.writeText(textToCopy);
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
        } catch (err) {
            console.error('Copy failed:', err);
        }
    }

    async function handleSubmit(e: FormEvent) {
        console.log(" Submit clicked");
        e.preventDefault();
        setOutput('');
        setLoading(true);

        const jwt = await getToken();
        console.log("JWT:", jwt);

        const controller = new AbortController();
        const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? '';
        setErrorMessage('');
        setRequestId('');
        setOutput('');
        let currentRequestId = '';

        const headers: Record<string, string> = {
            'Content-Type': 'application/json',
        };
        if (jwt) {
            headers.Authorization = `Bearer ${jwt}`;
        }

        await fetchEventSource(`${apiUrl}/api/v1/consultation`, {
            signal: controller.signal,
            method: 'POST',
            headers,
            body: JSON.stringify({
                patient_name: patientName,
                sender_name: senderName,
                date_of_visit: visitDate?.toISOString().slice(0, 10),
                notes,
            }),
            async onopen(response) {
                const headerRequestId = response.headers.get('x-request-id')?.trim() || '';
                if (headerRequestId) {
                    currentRequestId = headerRequestId;
                    setRequestId(headerRequestId);
                }

                if (!response.ok) {
                    throw buildConsultationError(
                        `Consultation request failed with status ${response.status}`,
                        response.status,
                        headerRequestId,
                    );
                }

                const contentType = response.headers.get('content-type') ?? '';
                if (!contentType.includes('text/event-stream')) {
                    throw buildConsultationError(
                        `Expected text/event-stream but received ${contentType || 'unknown content type'}`,
                        response.status,
                        headerRequestId,
                    );
                }
            },
            onmessage(ev) {
                console.log("DATA:", ev.data);
                setOutput(prev => `${prev}${ev.data}\n`);
            },
            onclose() {
                setLoading(false);
            },
            onerror(err: ConsultationStreamError) {
                const trackedRequestId = err.requestId || currentRequestId;
                console.error('SSE error:', err, trackedRequestId ? `(request_id=${trackedRequestId})` : '');
                if (trackedRequestId) {
                    setRequestId(trackedRequestId);
                }

                if (err?.status === 429) {
                    setErrorMessage('Too many requests. Please wait a moment and try again.');
                } else {
                    setErrorMessage('Something went wrong. Please try again.');
                }

                setLoading(false);
                controller.abort();
            },
        });
    }

    return (
        <div className="container mx-auto px-4 py-12 max-w-3xl">
            <h1 className="text-4xl font-bold text-gray-900 dark:text-gray-100 mb-8">
                Consultation Notes
            </h1>

            <form onSubmit={handleSubmit} className="space-y-6 bg-white dark:bg-gray-800 rounded-xl shadow-lg p-8">
                <div className="space-y-2">
                    <label htmlFor="patient" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                        Patient Name
                    </label>
                    <input
                        id="patient"
                        type="text"
                        value={patientName}
                        onChange={(e) => setPatientName(e.target.value)}
                        className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:text-white"
                        placeholder="Leave blank if you don't want to personalize the email"
                    />
                </div>

                <div className="space-y-2">
                    <label htmlFor="senderName" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                        Sender / Clinic Name <span className="text-gray-400 font-normal">(optional)</span>
                    </label>
                    <input
                        id="senderName"
                        type="text"
                        value={senderName}
                        onChange={(e) => setSenderName(e.target.value)}
                        className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:text-white"
                        placeholder="Dr. Sharma Clinic"
                    />
                </div>

                <div className="space-y-2">
                    <label htmlFor="patientEmail" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                        Patient Email <span className="text-gray-400 font-normal">(optional)</span>
                    </label>
                    <input
                        id="patientEmail"
                        type="email"
                        value={patientEmail}
                        onChange={(e) => setPatientEmail(e.target.value)}
                        className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:text-white"
                        placeholder="patient@example.com"
                    />
                </div>

                <div className="space-y-2">
                    <label htmlFor="patientPhone" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                        Patient Phone (WhatsApp) <span className="text-gray-400 font-normal">(optional)</span>
                    </label>
                    <input
                        id="patientPhone"
                        type="tel"
                        value={patientPhone}
                        onChange={(e) => setPatientPhone(e.target.value)}
                        className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:text-white"
                        placeholder="+91 98765 43210"
                    />
                </div>

                <div className="space-y-2">
                    <label htmlFor="date" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                        Date of Visit
                    </label>
                    <DatePicker
                        id="date"
                        selected={visitDate}
                        onChange={(d: Date | null) => setVisitDate(d)}
                        dateFormat="yyyy-MM-dd"
                        placeholderText="Select date"
                        required
                        className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:text-white"
                    />
                </div>

                <div className="space-y-2">
                    <label htmlFor="notes" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                        Consultation Notes
                    </label>
                    <textarea
                        id="notes"
                        required
                        rows={8}
                        value={notes}
                        onChange={(e) => setNotes(e.target.value)}
                        className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:text-white"
                        placeholder="Enter detailed consultation notes..."
                    />
                </div>

                <button 
                    type="submit" 
                    disabled={loading}
                    className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white font-semibold py-3 px-6 rounded-lg transition-colors duration-200"
                >
                    {loading ? 'Generating Summary...' : 'Generate Summary'}
                </button>

                {errorMessage && (
                    <div className="mt-3 space-y-1">
                        <p className="text-sm text-red-600 dark:text-red-400">
                            {errorMessage}
                        </p>
                        {requestId && (
                            <p className="text-xs text-gray-600 dark:text-gray-300">
                                Reference ID: {requestId}
                            </p>
                        )}
                    </div>
                )}
            </form>

            {output && (
                <section className="mt-8 bg-gray-50 dark:bg-gray-800 rounded-xl shadow-lg p-8">
                    <div className="markdown-content prose prose-blue dark:prose-invert max-w-none">
                        <ReactMarkdown remarkPlugins={[remarkGfm, remarkBreaks]}>
                            {buildEmailPreviewMarkdown()}
                        </ReactMarkdown>
                    </div>

                    {output.length > 1500 && (
                        <p className="mt-4 text-sm text-amber-600 dark:text-amber-400">
                            This draft is long — if the full content doesn&apos;t appear in Gmail or WhatsApp, please use the Copy button instead.
                        </p>
                    )}

                    <div className="mt-6 flex flex-wrap gap-3">
                        <a
                            href={buildGmailUrl()}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center px-4 py-2 bg-red-500 hover:bg-red-600 text-white text-sm font-medium rounded-lg transition-colors duration-200"
                        >
                            Send via Gmail
                        </a>

                        {patientPhone.trim() && (
                            <a
                                href={buildWhatsAppUrl()}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="inline-flex items-center px-4 py-2 bg-green-500 hover:bg-green-600 text-white text-sm font-medium rounded-lg transition-colors duration-200"
                            >
                                Send via WhatsApp
                            </a>
                        )}

                        <button
                            type="button"
                            onClick={handleCopy}
                            className="inline-flex items-center px-4 py-2 bg-gray-200 hover:bg-gray-300 dark:bg-gray-700 dark:hover:bg-gray-600 text-gray-800 dark:text-gray-100 text-sm font-medium rounded-lg transition-colors duration-200"
                        >
                            {copied ? 'Copied!' : 'Copy'}
                        </button>
                    </div>
                </section>
            )}
        </div>
    );
}

export default function Product() {
    return (
        <main className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-900 dark:to-gray-800">
            {/* User Menu in Top Right */}
            <div className="absolute top-4 right-4">
                <UserButton showName={true} />
            </div>

            <ConsultationForm />
        </main>
    );
}