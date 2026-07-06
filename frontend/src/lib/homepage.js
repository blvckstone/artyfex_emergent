import { api } from "@/lib/api";

export const fetchHomepage = () => api.get("/homepage").then((r) => r.data);
