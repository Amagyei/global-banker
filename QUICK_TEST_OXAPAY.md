# Quick Test Guide for OXA Pay

## Option 1: Test with API Key as Argument

```bash
python3 test_oxapay_with_key.py YOUR_API_KEY_HERE
```

## Option 2: Set Environment Variable

```bash
export OXAPAY_API_KEY=YOUR_API_KEY_HERE
python3 test_oxapay.py
```

## Option 3: Add to .env File

Add this line to your `.env` file:
```
OXAPAY_API_KEY=YOUR_API_KEY_HERE
```

Then run:
```bash
python3 test_oxapay.py
```

## What Gets Tested

1. ✅ Client initialization
2. ✅ Static address generation
3. ✅ White-label payment generation
4. ✅ API endpoints (networks, wallet)

## Expected Output

If successful, you should see:
- ✅ Static address generated with track_id and address
- ✅ White-label payment generated with payment details
- ✅ All API endpoints responding correctly

## Common Issues

1. **Invalid API Key**: Check your API key in OXA Pay dashboard
2. **Network Name Mismatch**: Ensure network names match OXA Pay's format
3. **API Rate Limits**: OXA Pay may have rate limits on test calls

