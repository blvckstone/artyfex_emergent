import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API = `${BACKEND_URL}/api`;

export const api = axios.create({
  baseURL: API,
  headers: { "Content-Type": "application/json" },
});

export const fetchProducts = () => api.get("/products").then((r) => r.data);
export const fetchReviews = () => api.get("/reviews").then((r) => r.data);
export const createOrder = (payload) => api.post("/orders", payload).then((r) => r.data);
export const createB2BLead = (payload) => api.post("/b2b/leads", payload).then((r) => r.data);
