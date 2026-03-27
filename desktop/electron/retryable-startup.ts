export class RetryableStartup {
  private currentRun: Promise<void> | null = null;

  run(bootstrap: () => Promise<void>) {
    if (this.currentRun) {
      return this.currentRun;
    }

    this.currentRun = bootstrap().catch((error: unknown) => {
      this.currentRun = null;
      throw error;
    });

    return this.currentRun;
  }

  reset() {
    this.currentRun = null;
  }
}
