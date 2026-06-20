// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/token/ERC721/extensions/ERC721URIStorage.sol";
import "@openzeppelin/contracts/token/ERC721/extensions/ERC721Enumerable.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "./interfaces/IPalasirionNFT.sol";

/**
 * @title PalasirionNFT
 * @notice ERC-721 Soulbound-like per diritti d'uso Palasirion — ASD Millennio.
 *         Il token NON è uno strumento finanziario (MiFID II).
 *         Trasferibilità bloccata: solo il contratto può trasferire (escrow → socio).
 */
contract PalasirionNFT is
    ERC721,
    ERC721URIStorage,
    ERC721Enumerable,
    Ownable,
    IPalasirionNFT
{
    uint256 private _nextTokenId;

    mapping(address => bool) private _minters;
    mapping(string => bool) private _bookedSlots;
    mapping(uint256 => string) private _tokenSlotKeys;
    mapping(uint256 => string[]) private _tokenSlotKeysList;
    mapping(uint256 => string) private _tokenIcalHashes;

    modifier onlyMinter() {
        require(_minters[msg.sender] || msg.sender == owner(), "PalasirionNFT: non autorizzato");
        _;
    }

    constructor(address initialOwner) ERC721("Palasirion Diritto d'Uso", "PALA") Ownable(initialOwner) {
        _minters[initialOwner] = true;
    }

    // ─── Minting ────────────────────────────────────────────────────────────────

    function mintNFT(
        address to,
        string memory uri
    ) external onlyMinter returns (uint256) {
        uint256 tokenId = _nextTokenId++;
        _safeMint(address(this), tokenId);
        _setTokenURI(tokenId, uri);
        _safeTransfer(address(this), to, tokenId, "");
        return tokenId;
    }

    /**
     * @notice Versione avanzata con registrazione slot e hash iCal on-chain.
     */
    function mintNFTWithSlot(
        address to,
        string memory uri,
        string memory slotKey,
        string memory icalHash
    ) external onlyMinter returns (uint256) {
        require(!_bookedSlots[slotKey], "PalasirionNFT: slot gia prenotato");

        uint256 tokenId = _nextTokenId++;
        _safeMint(address(this), tokenId);
        _setTokenURI(tokenId, uri);

        _bookedSlots[slotKey] = true;
        _tokenSlotKeys[tokenId] = slotKey;
        _tokenIcalHashes[tokenId] = icalHash;

        _safeTransfer(address(this), to, tokenId, "");

        emit SlotBooked(tokenId, to, icalHash, slotKey);
        return tokenId;
    }

    /**
     * @notice Minta un NFT prenotando PIÙ slot per-ora in un'unica transazione.
     *         Reverta se anche un solo slotKey è già prenotato (anti double-sell on-chain).
     *         Usato dal backend: un acquisto = un NFT con tutte le ore scelte.
     */
    function mintNFTWithSlots(
        address to,
        string memory uri,
        string[] memory slotKeys,
        string memory icalHash
    ) external onlyMinter returns (uint256) {
        require(slotKeys.length > 0, "PalasirionNFT: nessuno slot");
        for (uint256 i = 0; i < slotKeys.length; i++) {
            require(!_bookedSlots[slotKeys[i]], "PalasirionNFT: slot gia prenotato");
        }

        uint256 tokenId = _nextTokenId++;
        _safeMint(address(this), tokenId);
        _setTokenURI(tokenId, uri);

        for (uint256 i = 0; i < slotKeys.length; i++) {
            _bookedSlots[slotKeys[i]] = true;
            _tokenSlotKeysList[tokenId].push(slotKeys[i]);
            emit SlotBooked(tokenId, to, icalHash, slotKeys[i]);
        }
        _tokenIcalHashes[tokenId] = icalHash;

        _safeTransfer(address(this), to, tokenId, "");
        return tokenId;
    }

    // ─── Query ──────────────────────────────────────────────────────────────────

    function getTokensByOwner(address ownerAddr) external view returns (uint256[] memory) {
        uint256 count = balanceOf(ownerAddr);
        uint256[] memory tokens = new uint256[](count);
        for (uint256 i = 0; i < count; i++) {
            tokens[i] = tokenOfOwnerByIndex(ownerAddr, i);
        }
        return tokens;
    }

    function isSlotBooked(string memory slotKey) external view returns (bool) {
        return _bookedSlots[slotKey];
    }

    function getTokenSlotKey(uint256 tokenId) external view returns (string memory) {
        return _tokenSlotKeys[tokenId];
    }

    function getTokenIcalHash(uint256 tokenId) external view returns (string memory) {
        return _tokenIcalHashes[tokenId];
    }

    function getTokenSlotKeys(uint256 tokenId) external view returns (string[] memory) {
        return _tokenSlotKeysList[tokenId];
    }

    // ─── Gestione minter ────────────────────────────────────────────────────────

    function addMinter(address minter) external onlyOwner {
        _minters[minter] = true;
    }

    function removeMinter(address minter) external onlyOwner {
        _minters[minter] = false;
    }

    function isMinter(address addr) external view returns (bool) {
        return _minters[addr];
    }

    /**
     * @notice Aggiorna l'URI dei metadati IPFS dopo il mint (necessario per includere il token_id reale).
     * @dev Chiamabile solo dal minter. Richiede che il token esista già.
     */
    function updateTokenURI(uint256 tokenId, string memory newUri) external onlyMinter {
        require(_ownerOf(tokenId) != address(0), "PalasirionNFT: token inesistente");
        _setTokenURI(tokenId, newUri);
    }

    /**
     * @notice Aggiorna l'hash iCal on-chain dopo il mint finale.
     */
    function updateIcalHash(uint256 tokenId, string memory newIcalHash) external onlyMinter {
        require(_ownerOf(tokenId) != address(0), "PalasirionNFT: token inesistente");
        _tokenIcalHashes[tokenId] = newIcalHash;
    }

    // ─── Trasferibilità bloccata (Soulbound) ─────────────────────────────────────
    // Il token è non trasferibile dopo l'emissione.
    // Il mint usa _safeMint + _safeTransfer internamente (percorsi interni, non pubblici).

    function transferFrom(
        address,
        address,
        uint256
    ) public pure override(ERC721, IERC721) {
        revert("PalasirionNFT: token non trasferibile");
    }

    function safeTransferFrom(
        address,
        address,
        uint256,
        bytes memory
    ) public pure override(ERC721, IERC721) {
        revert("PalasirionNFT: token non trasferibile");
    }

    // ─── Override obbligatori per compatibilità OpenZeppelin ────────────────────

    function _update(
        address to,
        uint256 tokenId,
        address auth
    ) internal override(ERC721, ERC721Enumerable) returns (address) {
        return super._update(to, tokenId, auth);
    }

    function _increaseBalance(
        address account,
        uint128 value
    ) internal override(ERC721, ERC721Enumerable) {
        // solhint-disable-next-line no-empty-blocks
        /* istanbul ignore next */
        super._increaseBalance(account, value);
    }

    function tokenURI(uint256 tokenId)
        public
        view
        override(ERC721, ERC721URIStorage, IPalasirionNFT)
        returns (string memory)
    {
        return super.tokenURI(tokenId);
    }

    function supportsInterface(bytes4 interfaceId)
        public
        view
        override(ERC721, ERC721URIStorage, ERC721Enumerable)
        returns (bool)
    {
        return super.supportsInterface(interfaceId);
    }

    function onERC721Received(
        address,
        address,
        uint256,
        bytes memory
    ) public pure returns (bytes4) {
        return this.onERC721Received.selector;
    }
}
