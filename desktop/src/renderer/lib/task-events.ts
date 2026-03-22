export type BackendHealth = {
  status: "ok";
  service: string;
};

export type BackendStatus =
  | {
      state: "starting";
      message: string;
    }
  | {
      state: "ready";
      baseUrl: string;
      health: BackendHealth;
    }
  | {
      state: "error";
      message: string;
    };
