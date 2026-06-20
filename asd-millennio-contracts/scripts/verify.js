const { run, ethers } = require("hardhat");

async function main() {
  const contractAddress = process.env.CONTRACT_ADDRESS;
  if (!contractAddress) {
    throw new Error("CONTRACT_ADDRESS non impostata nel .env");
  }

  const [deployer] = await ethers.getSigners();

  console.log("Verifica contratto:", contractAddress);

  await run("verify:verify", {
    address: contractAddress,
    constructorArguments: [deployer.address],
  });

  console.log("Contratto verificato su Polygonscan.");
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
