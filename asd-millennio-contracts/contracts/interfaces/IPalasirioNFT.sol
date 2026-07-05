// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

interface IPalasirioNFT {
    event SlotBooked(
        uint256 indexed tokenId,
        address indexed member,
        string icalHash,
        string slotKey
    );

    function mintNFT(address to, string memory tokenURI) external returns (uint256);
    function mintNFTWithSlots(
        address to,
        string memory uri,
        string[] memory slotKeys,
        string memory icalHash
    ) external returns (uint256);
    function tokenURI(uint256 tokenId) external view returns (string memory);
    function getTokensByOwner(address owner) external view returns (uint256[] memory);
    function getTokenSlotKeys(uint256 tokenId) external view returns (string[] memory);
    function isSlotBooked(string memory slotKey) external view returns (bool);
    function addMinter(address minter) external;
    function removeMinter(address minter) external;
    function updateTokenURI(uint256 tokenId, string memory newUri) external;
    function updateIcalHash(uint256 tokenId, string memory newIcalHash) external;
}
