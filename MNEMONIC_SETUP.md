# Setting Up Mnemonic in .env File

## ⚠️ Security Warning

**Storing your mnemonic in a file is less secure than entering it interactively.**

However, if you choose to do this:

1. ✅ **Make sure `.env` is in `.gitignore`** (it should be already)
2. ✅ **Never commit `.env` to git**
3. ✅ **Only use this for testnet/test wallets**
4. ✅ **Delete the mnemonic from `.env` after deriving the vpub**

## How to Add Mnemonic to .env

1. Open `.env` file in the `global_banker` directory

2. Add this line:
   ```
   MNEMONIC=word1 word2 word3 word4 word5 word6 word7 word8 word9 word10 word11 word12
   ```
   
   Replace with your actual 12 or 24 words.

3. **Example** (don't use this - it's just an example):
   ```
   MNEMONIC=abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about
   ```

4. Save the file

5. Run the derivation script:
   ```bash
   python derive_vpub_from_seed.py
   ```
   
   It will automatically read from the `.env` file.

## After Deriving the vpub

**IMPORTANT**: Once you have the vpub, **remove the MNEMONIC line from `.env`** for security!

The vpub is safe to keep (it's a public key), but the mnemonic should be removed.

## Alternative: Use Environment Variable

Instead of `.env`, you can set it as an environment variable:

```bash
export MNEMONIC="word1 word2 word3 ... word12"
python derive_vpub_from_seed.py
```

This is slightly more secure as it's not stored in a file.

