import { Config, getConfig } from "../config";

describe("Bridge maintenance mode", () => {
  let config: Config;

  beforeEach(async () => {
    config = await getConfig();
  })

  it("pause sending transfers", async () => {
    const {eth, red} = config;

    
  });
});

