const hre = require("hardhat");

async function main() {
  const [deployer] = await hre.ethers.getSigners();
  console.log("Deploying contracts with the account:", deployer.address);

  const Escrow = await hre.ethers.getContractFactory("AgentEscrow");
  const escrow = await Escrow.deploy();

  await escrow.waitForDeployment();

  const address = await escrow.getAddress();
  console.log("AgentEscrow deployed to:", address);
  console.log("Explorer Link: https://www.okx.com/explorer/xlayer-test/address/" + address);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
