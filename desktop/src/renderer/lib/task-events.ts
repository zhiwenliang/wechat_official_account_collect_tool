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
      health: BackendHealth;
    }
  | {
      state: "error";
      message: string;
    };
