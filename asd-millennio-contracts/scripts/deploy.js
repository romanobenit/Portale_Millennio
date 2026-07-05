const { ethers } = require("hardhat");

async function main() {
  const [deployer] = await ethers.getSigners();
  console.log("Deploy con account:", deployer.address);
  console.log("Balance:", ethers.formatEther(await ethers.provider.getBalance(deployer.address)), "MATIC");

  const PalasirioNFT = await ethers.getContractFactory("PalasirioNFT");
  const contract = await PalasirioNFT.deploy(deployer.address);
  await contract.waitForDeployment();

  const address = await contract.getAddress();
  console.log("PalasirioNFT deployato a:", address);
  console.log("Network:", (await ethers.provider.getNetwork()).name);
  console.log("Transaction hash:", contract.deploymentTransaction().hash);

  console.log("\nAggiorna il .env:");
  console.log(`CONTRACT_ADDRESS_PALASIRIO_NFT=${address}`);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
