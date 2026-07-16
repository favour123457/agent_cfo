require("@nomicfoundation/hardhat-toolbox");
require("dotenv").config({ path: '../backend/.env' });

/** @type import('hardhat/config').HardhatUserConfig */
module.exports = {
  solidity: "0.8.19",
  paths: {
    sources: "./src"
  },
  networks: {
    xlayerTestnet: {
      url: "https://testrpc.xlayer.tech",
      accounts: process.env.ASP_PRIVATE_KEY ? [process.env.ASP_PRIVATE_KEY] : [],
    }
  }
};
