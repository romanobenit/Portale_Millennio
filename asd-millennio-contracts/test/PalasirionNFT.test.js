const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("PalasirionNFT", function () {
  let contract;
  let owner, minter, user1, user2;

  beforeEach(async function () {
    [owner, minter, user1, user2] = await ethers.getSigners();
    const Factory = await ethers.getContractFactory("PalasirionNFT");
    contract = await Factory.deploy(owner.address);
    await contract.waitForDeployment();
  });

  // ─── Deploy ──────────────────────────────────────────────────────────────────

  describe("Deploy", function () {
    it("ha il nome e simbolo corretti", async function () {
      expect(await contract.name()).to.equal("Palasirion Diritto d'Uso");
      expect(await contract.symbol()).to.equal("PALA");
    });

    it("owner è minter di default", async function () {
      expect(await contract.isMinter(owner.address)).to.be.true;
    });

    it("utente normale non è minter", async function () {
      expect(await contract.isMinter(user1.address)).to.be.false;
    });
  });

  // ─── Gestione minter ─────────────────────────────────────────────────────────

  describe("Gestione minter", function () {
    it("owner può aggiungere minter", async function () {
      await contract.connect(owner).addMinter(minter.address);
      expect(await contract.isMinter(minter.address)).to.be.true;
    });

    it("owner può rimuovere minter", async function () {
      await contract.connect(owner).addMinter(minter.address);
      await contract.connect(owner).removeMinter(minter.address);
      expect(await contract.isMinter(minter.address)).to.be.false;
    });

    it("non-owner non può aggiungere minter", async function () {
      await expect(
        contract.connect(user1).addMinter(user2.address)
      ).to.be.revertedWithCustomError(contract, "OwnableUnauthorizedAccount");
    });

    it("non-owner non può rimuovere minter", async function () {
      await contract.connect(owner).addMinter(minter.address);
      await expect(
        contract.connect(user1).removeMinter(minter.address)
      ).to.be.revertedWithCustomError(contract, "OwnableUnauthorizedAccount");
    });
  });

  // ─── Minting ─────────────────────────────────────────────────────────────────

  describe("mintNFT", function () {
    it("owner può mintare NFT", async function () {
      const uri = "ipfs://QmTestHash1234";
      const tx = await contract.connect(owner).mintNFT(user1.address, uri);
      await tx.wait();
      expect(await contract.balanceOf(user1.address)).to.equal(1);
    });

    it("minter autorizzato può mintare", async function () {
      await contract.connect(owner).addMinter(minter.address);
      await contract.connect(minter).mintNFT(user1.address, "ipfs://QmTest");
      expect(await contract.balanceOf(user1.address)).to.equal(1);
    });

    it("non-minter non può mintare", async function () {
      await expect(
        contract.connect(user1).mintNFT(user2.address, "ipfs://QmTest")
      ).to.be.revertedWith("PalasirionNFT: non autorizzato");
    });

    it("tokenURI è impostato correttamente", async function () {
      const uri = "ipfs://QmAbcDef123456";
      await contract.connect(owner).mintNFT(user1.address, uri);
      expect(await contract.tokenURI(0)).to.equal(uri);
    });

    it("minting incrementa il token ID", async function () {
      await contract.connect(owner).mintNFT(user1.address, "ipfs://uri1");
      await contract.connect(owner).mintNFT(user1.address, "ipfs://uri2");
      expect(await contract.balanceOf(user1.address)).to.equal(2);
      expect(await contract.tokenURI(1)).to.equal("ipfs://uri2");
    });
  });

  // ─── mintNFTWithSlot ─────────────────────────────────────────────────────────

  describe("mintNFTWithSlot", function () {
    const slotKey = "2027-03-02_mattina";
    const icalHash = "sha256_abc123";
    const uri = "ipfs://QmMetadata";

    it("minta con slot key e emette evento SlotBooked", async function () {
      const tx = await contract
        .connect(owner)
        .mintNFTWithSlot(user1.address, uri, slotKey, icalHash);
      const receipt = await tx.wait();

      const event = receipt.logs.find(
        (log) => log.fragment && log.fragment.name === "SlotBooked"
      );
      expect(event).to.not.be.undefined;
      expect(event.args.member).to.equal(user1.address);
      expect(event.args.icalHash).to.equal(icalHash);
      expect(event.args.slotKey).to.equal(slotKey);
    });

    it("slot risulta prenotato dopo il mint", async function () {
      await contract.connect(owner).mintNFTWithSlot(user1.address, uri, slotKey, icalHash);
      expect(await contract.isSlotBooked(slotKey)).to.be.true;
    });

    it("slot diverso risulta libero", async function () {
      expect(await contract.isSlotBooked("2027-03-04_pomeriggio")).to.be.false;
    });

    it("non può prenotare lo stesso slot due volte", async function () {
      await contract.connect(owner).mintNFTWithSlot(user1.address, uri, slotKey, icalHash);
      await expect(
        contract.connect(owner).mintNFTWithSlot(user2.address, uri, slotKey, icalHash)
      ).to.be.revertedWith("PalasirionNFT: slot gia prenotato");
    });

    it("hash iCal e slot key recuperabili on-chain", async function () {
      await contract.connect(owner).mintNFTWithSlot(user1.address, uri, slotKey, icalHash);
      expect(await contract.getTokenSlotKey(0)).to.equal(slotKey);
      expect(await contract.getTokenIcalHash(0)).to.equal(icalHash);
    });

    it("non-minter non può mintare con slot", async function () {
      await expect(
        contract.connect(user1).mintNFTWithSlot(user2.address, uri, slotKey, icalHash)
      ).to.be.revertedWith("PalasirionNFT: non autorizzato");
    });
  });

  // ─── mintNFTWithSlots (multi-ora) ────────────────────────────────────────────

  describe("mintNFTWithSlots", function () {
    const slotKeys = [
      "2027-03-02_mattina_08",
      "2027-03-02_mattina_09",
      "2027-03-02_mattina_10",
    ];
    const icalHash = "sha256_multi";
    const uri = "ipfs://QmMulti";

    it("minta un NFT prenotando tutte le ore", async function () {
      await contract.connect(owner).mintNFTWithSlots(user1.address, uri, slotKeys, icalHash);
      expect(await contract.balanceOf(user1.address)).to.equal(1);
      for (const k of slotKeys) {
        expect(await contract.isSlotBooked(k)).to.be.true;
      }
    });

    it("emette un evento SlotBooked per ogni ora", async function () {
      const tx = await contract.connect(owner).mintNFTWithSlots(user1.address, uri, slotKeys, icalHash);
      const receipt = await tx.wait();
      const events = receipt.logs.filter(
        (log) => log.fragment && log.fragment.name === "SlotBooked"
      );
      expect(events.length).to.equal(slotKeys.length);
      expect(events.map((e) => e.args.slotKey)).to.deep.equal(slotKeys);
    });

    it("getTokenSlotKeys restituisce l'array completo", async function () {
      await contract.connect(owner).mintNFTWithSlots(user1.address, uri, slotKeys, icalHash);
      expect(await contract.getTokenSlotKeys(0)).to.deep.equal(slotKeys);
    });

    it("reverta se anche una sola ora è già prenotata", async function () {
      await contract.connect(owner).mintNFTWithSlot(user1.address, uri, "2027-03-02_mattina_09", icalHash);
      await expect(
        contract.connect(owner).mintNFTWithSlots(user2.address, uri, slotKeys, icalHash)
      ).to.be.revertedWith("PalasirionNFT: slot gia prenotato");
    });

    it("la revert non lascia prenotazioni parziali (atomicità)", async function () {
      // 09 già preso → il mint di [08, 09, 10] deve revertare e NON prenotare 08 nè 10
      await contract.connect(owner).mintNFTWithSlot(user1.address, uri, "2027-03-02_mattina_09", icalHash);
      await expect(
        contract.connect(owner).mintNFTWithSlots(user2.address, uri, slotKeys, icalHash)
      ).to.be.reverted;
      expect(await contract.isSlotBooked("2027-03-02_mattina_08")).to.be.false;
      expect(await contract.isSlotBooked("2027-03-02_mattina_10")).to.be.false;
    });

    it("reverta con array di slot vuoto", async function () {
      await expect(
        contract.connect(owner).mintNFTWithSlots(user1.address, uri, [], icalHash)
      ).to.be.revertedWith("PalasirionNFT: nessuno slot");
    });

    it("non-minter non può mintare", async function () {
      await expect(
        contract.connect(user1).mintNFTWithSlots(user2.address, uri, slotKeys, icalHash)
      ).to.be.revertedWith("PalasirionNFT: non autorizzato");
    });
  });

  // ─── updateTokenURI / updateIcalHash ─────────────────────────────────────────

  describe("updateTokenURI / updateIcalHash", function () {
    const uri = "ipfs://QmInitial";
    const newUri = "ipfs://QmUpdated";
    const icalHash = "sha256_init";
    const newIcalHash = "sha256_updated";

    beforeEach(async function () {
      await contract.connect(owner).mintNFT(user1.address, uri);  // token 0
    });

    it("updateTokenURI aggiorna l'URI on-chain", async function () {
      await contract.connect(owner).updateTokenURI(0, newUri);
      expect(await contract.tokenURI(0)).to.equal(newUri);
    });

    it("updateTokenURI reverta su token inesistente", async function () {
      await expect(
        contract.connect(owner).updateTokenURI(999, newUri)
      ).to.be.revertedWith("PalasirionNFT: token inesistente");
    });

    it("updateTokenURI solo minter", async function () {
      await expect(
        contract.connect(user1).updateTokenURI(0, newUri)
      ).to.be.revertedWith("PalasirionNFT: non autorizzato");
    });

    it("updateIcalHash aggiorna l'hash on-chain", async function () {
      await contract.connect(owner).updateIcalHash(0, newIcalHash);
      expect(await contract.getTokenIcalHash(0)).to.equal(newIcalHash);
    });

    it("updateIcalHash reverta su token inesistente", async function () {
      await expect(
        contract.connect(owner).updateIcalHash(999, newIcalHash)
      ).to.be.revertedWith("PalasirionNFT: token inesistente");
    });

    it("updateIcalHash solo minter", async function () {
      await expect(
        contract.connect(user1).updateIcalHash(0, newIcalHash)
      ).to.be.revertedWith("PalasirionNFT: non autorizzato");
    });
  });

  // ─── Query token per owner ───────────────────────────────────────────────────

  describe("getTokensByOwner", function () {
    it("restituisce lista vuota per owner senza token", async function () {
      const tokens = await contract.getTokensByOwner(user1.address);
      expect(tokens.length).to.equal(0);
    });

    it("restituisce tutti i token dell'owner", async function () {
      await contract.connect(owner).mintNFT(user1.address, "ipfs://uri1");
      await contract.connect(owner).mintNFT(user1.address, "ipfs://uri2");
      await contract.connect(owner).mintNFT(user2.address, "ipfs://uri3");

      const tokensUser1 = await contract.getTokensByOwner(user1.address);
      expect(tokensUser1.length).to.equal(2);

      const tokensUser2 = await contract.getTokensByOwner(user2.address);
      expect(tokensUser2.length).to.equal(1);
    });
  });

  // ─── Soulbound — trasferibilità bloccata ─────────────────────────────────────

  describe("Soulbound — non trasferibile", function () {
    it("trasferimento diretto da user blocca con errore", async function () {
      await contract.connect(owner).mintNFT(user1.address, "ipfs://uri1");
      await expect(
        contract.connect(user1).transferFrom(user1.address, user2.address, 0)
      ).to.be.revertedWith("PalasirionNFT: token non trasferibile");
    });

    it("safeTransferFrom da user blocca con errore", async function () {
      await contract.connect(owner).mintNFT(user1.address, "ipfs://uri1");
      await expect(
        contract.connect(user1)["safeTransferFrom(address,address,uint256)"](
          user1.address, user2.address, 0
        )
      ).to.be.revertedWith("PalasirionNFT: token non trasferibile");
    });

    it("approve e poi transfer blocca ugualmente", async function () {
      await contract.connect(owner).mintNFT(user1.address, "ipfs://uri1");
      await contract.connect(user1).approve(user2.address, 0);
      await expect(
        contract.connect(user2).transferFrom(user1.address, user2.address, 0)
      ).to.be.revertedWith("PalasirionNFT: token non trasferibile");
    });
  });

  // ─── supportsInterface ───────────────────────────────────────────────────────

  describe("supportsInterface", function () {
    it("supporta ERC721", async function () {
      expect(await contract.supportsInterface("0x80ac58cd")).to.be.true;
    });

    it("supporta ERC721Enumerable", async function () {
      expect(await contract.supportsInterface("0x780e9d63")).to.be.true;
    });

    it("supporta ERC721Metadata", async function () {
      expect(await contract.supportsInterface("0x5b5e139f")).to.be.true;
    });

    it("restituisce false per interfaccia non supportata", async function () {
      expect(await contract.supportsInterface("0xdeadbeef")).to.be.false;
    });
  });

  // ─── Mint multipli e balanceOf ───────────────────────────────────────────────

  describe("Mint multipli e balanceOf", function () {
    it("balanceOf cresce correttamente con più mint", async function () {
      await contract.connect(owner).mintNFT(user1.address, "ipfs://uri1");
      await contract.connect(owner).mintNFT(user1.address, "ipfs://uri2");
      await contract.connect(owner).mintNFT(user1.address, "ipfs://uri3");
      expect(await contract.balanceOf(user1.address)).to.equal(3);
    });

    it("totalSupply rispecchia i token emessi", async function () {
      await contract.connect(owner).mintNFT(user1.address, "ipfs://uri1");
      await contract.connect(owner).mintNFT(user2.address, "ipfs://uri2");
      expect(await contract.totalSupply()).to.equal(2);
    });
  });

  // ─── Trasferimento dal contratto (percorso mint interno) ─────────────────────

  describe("Trasferimento dal contratto — percorso interno mint", function () {
    it("il mint deposita prima nel contratto poi trasferisce all'owner", async function () {
      // mintNFT usa _safeMint(address(this)) + _safeTransfer(this → user)
      // Verifica che dopo il mint il token sia effettivamente nell'account del socio
      const tx = await contract.connect(owner).mintNFT(user1.address, "ipfs://uri1");
      await tx.wait();
      expect(await contract.ownerOf(0)).to.equal(user1.address);
      expect(await contract.balanceOf(user1.address)).to.equal(1);
    });

    it("mintNFTWithSlot trasferisce correttamente il token al destinatario", async function () {
      await contract.connect(owner).mintNFTWithSlot(
        user1.address, "ipfs://uriSlot", "2027-04-01_notte", "hash123"
      );
      expect(await contract.ownerOf(0)).to.equal(user1.address);
    });

    it("il contratto non trattiene nessun token dopo il mint", async function () {
      await contract.connect(owner).mintNFT(user1.address, "ipfs://uri1");
      await contract.connect(owner).mintNFT(user2.address, "ipfs://uri2");
      // Il contratto stesso non deve possedere token dopo il mint
      const contractBalance = await contract.balanceOf(await contract.getAddress());
      expect(contractBalance).to.equal(0);
    });
  });

  // ─── Gestione minter avanzata ────────────────────────────────────────────────

  describe("Gestione minter avanzata", function () {
    it("minter rimosso non può più mintare", async function () {
      await contract.connect(owner).addMinter(minter.address);
      await contract.connect(owner).removeMinter(minter.address);
      await expect(
        contract.connect(minter).mintNFT(user1.address, "ipfs://uri1")
      ).to.be.revertedWith("PalasirionNFT: non autorizzato");
    });

    it("isMinter ritorna false per address zero", async function () {
      expect(await contract.isMinter(ethers.ZeroAddress)).to.be.false;
    });

    it("owner può mintare anche se rimosso dai minter espliciti (percorso owner=true)", async function () {
      // Rimuovi owner dai _minters espliciti → il controllo cade su msg.sender == owner()
      // Copre il branch [_minters[msg.sender]=false, owner()=true] nel modificatore onlyMinter
      await contract.connect(owner).removeMinter(owner.address);
      expect(await contract.isMinter(owner.address)).to.be.false;

      // Owner può ancora mintare tramite la condizione owner()
      await contract.connect(owner).mintNFT(user1.address, "ipfs://uri1");
      expect(await contract.balanceOf(user1.address)).to.equal(1);
    });

    it("address sconosciuto non è owner e non è minter — revert", async function () {
      await expect(
        contract.connect(user2).mintNFT(user1.address, "ipfs://uri1")
      ).to.be.revertedWith("PalasirionNFT: non autorizzato");
    });
  });

  // ─── _increaseBalance — copertura interna ────────────────────────────────────

  describe("_increaseBalance — copertura override interno", function () {
    it("il balance aumenta correttamente dopo N mint (verifica _increaseBalance chain)", async function () {
      // Ogni mint chiama _update → _increaseBalance; questo test ne forza l'esecuzione ripetuta
      for (let i = 0; i < 5; i++) {
        await contract.connect(owner).mintNFT(user1.address, `ipfs://uri${i}`);
      }
      expect(await contract.balanceOf(user1.address)).to.equal(5);
      expect(await contract.totalSupply()).to.equal(5);
    });

    it("balance corretto con mint su account diversi", async function () {
      await contract.connect(owner).mintNFT(user1.address, "ipfs://a");
      await contract.connect(owner).mintNFT(user2.address, "ipfs://b");
      await contract.connect(owner).mintNFT(user1.address, "ipfs://c");
      expect(await contract.balanceOf(user1.address)).to.equal(2);
      expect(await contract.balanceOf(user2.address)).to.equal(1);
    });
  });

  // ─── onERC721Received ────────────────────────────────────────────────────────

  describe("onERC721Received", function () {
    it("il contratto implementa IERC721Receiver (necessario per safeMint su se stesso)", async function () {
      const selector = await contract.onERC721Received(
        ethers.ZeroAddress,
        ethers.ZeroAddress,
        0,
        "0x"
      );
      // Deve restituire il selector corretto: bytes4(keccak256("onERC721Received(address,address,uint256,bytes)"))
      expect(selector).to.equal("0x150b7a02");
    });
  });
});
