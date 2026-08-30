import axios from "axios";
const baseURL = import.meta.env.VITE_API_BASE_URL;
if (!baseURL) {
    throw new Error("VITE_API_BASE_URL is missing. Check the active Vite environment file.");
}
export const api = axios.create({
    baseURL: baseURL.replace(/\/+$/, ""),
    timeout: 10_000,
});
