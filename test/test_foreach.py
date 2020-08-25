import torch
from torch.testing._internal.common_utils import TestCase, run_tests
from torch.testing._internal.common_device_type import instantiate_device_type_tests, dtypes

class TestForeach(TestCase):
    bin_ops = [
        torch._foreach_add, 
        torch._foreach_add_,
        torch._foreach_sub,
        torch._foreach_sub_,
        torch._foreach_mul, 
        torch._foreach_mul_, 
        torch._foreach_div, 
        torch._foreach_div_,
        ]

    #
    # Unary ops
    #
    @dtypes(*[torch.float, torch.double, torch.complex64, torch.complex128])
    def test_sqrt(self, device, dtype):
        tensors = [torch.ones(2, 2, device=device, dtype=dtype) for _ in range(2)]

        exp = [torch.sqrt(t) for t in tensors]
        res = torch._foreach_sqrt(tensors)
        torch._foreach_sqrt_(tensors)

        self.assertEqual([torch.sqrt(torch.ones(2, 2, device=device, dtype=dtype)) for _ in range(2)], res)
        self.assertEqual(tensors, res)
        self.assertEqual(exp, res)

    @dtypes(*[torch.float, torch.double, torch.complex64, torch.complex128])
    def test_exp(self, device, dtype):
        tensors = [torch.ones(20, 20, device=device, dtype=dtype) for _ in range(20)]

        res = torch._foreach_exp(tensors)
        torch._foreach_exp_(tensors)

        self.assertEqual([torch.exp(torch.ones(20, 20, device=device, dtype=dtype)) for _ in range(20)], res)
        self.assertEqual(tensors, res)

    #
    # Pointwise ops
    #
    @dtypes(*torch.testing.get_all_dtypes(include_bfloat16=False, include_bool=False, include_complex=False))
    def test_addcmul(self, device, dtype):
        if device == 'cpu':
            if dtype in [torch.bfloat16, torch.half]:
                return

        tensors = [torch.ones(20, 20, device=device, dtype=dtype) for n in range(20)]
        tensors1 = [torch.ones(20, 20, device=device, dtype=dtype) for n in range(20)]
        tensors2 = [torch.ones(20, 20, device=device, dtype=dtype) for n in range(20)]

        res = torch._foreach_addcmul(tensors, tensors1, tensors2, 2)
        self.assertEqual([tensors[n].addcmul(tensors1[n], tensors2[n], value=2) for n in range(20)], res)

        torch._foreach_addcmul_(tensors, tensors1, tensors2, 2)
        self.assertEqual(res, tensors)

    @dtypes(*torch.testing.get_all_dtypes(include_bfloat16=False, include_bool=False, include_complex=False))
    def test_addcdiv(self, device, dtype):
        if dtype in [torch.int8, torch.int16, torch.int32, torch.int64, torch.uint8]:
            # Integer division of tensors using div or / is no longer supported
            return

        if device == 'cpu':
            if dtype in [torch.bfloat16, torch.half]:
                return

        tensors = [torch.ones(20, 20, device=device, dtype=dtype) for n in range(20)]
        tensors1 = [torch.ones(20, 20, device=device, dtype=dtype) for n in range(20)]
        tensors2 = [torch.ones(20, 20, device=device, dtype=dtype) for n in range(20)]

        res = torch._foreach_addcdiv(tensors, tensors1, tensors2, 2)
        self.assertEqual([tensors[n].addcdiv(tensors1[n], tensors2[n], value=2) for n in range(20)], res)

        torch._foreach_addcdiv_(tensors, tensors1, tensors2, 2)
        self.assertEqual(res, tensors)

    #
    # Ops with scalar
    #
    @dtypes(*torch.testing.get_all_dtypes())
    def test_int_scalar(self, device, dtype):
        tensors = [torch.zeros(10, 10, device=device, dtype=dtype) for _ in range(10)]
        int_scalar = 1

        # bool tensor + 1 will result in int64 tensor
        if dtype == torch.bool:
            expected = [torch.ones(10, 10, device=device, dtype=torch.int64) for _ in range(10)]
        else:
            expected = [torch.ones(10, 10, device=device, dtype=dtype) for _ in range(10)]

        res = torch._foreach_add(tensors, int_scalar)
        self.assertEqual(res, expected)

        if dtype in [torch.bool]:
            with self.assertRaisesRegex(RuntimeError, "result type Long can't be cast to the desired output type Bool"):
                torch._foreach_add_(tensors, int_scalar)
        else:
            torch._foreach_add_(tensors, int_scalar)
            self.assertEqual(res, tensors)

    @dtypes(*torch.testing.get_all_dtypes())
    def test_float_scalar(self, device, dtype):
        tensors = [torch.zeros(10, 10, device=device, dtype=dtype) for _ in range(10)]
        float_scalar = 1.

        # float scalar + integral tensor will result in float tensor
        if dtype in [torch.uint8, torch.int8, torch.int16, 
                     torch.int32, torch.int64, torch.bool]:
            expected = [torch.ones(10, 10, device=device, dtype=torch.float32) for _ in range(10)]
        else:
            expected = [torch.ones(10, 10, device=device, dtype=dtype) for _ in range(10)]

        res = torch._foreach_add(tensors, float_scalar)
        self.assertEqual(res, expected)

        if dtype in [torch.uint8, torch.int8, torch.int16, 
                     torch.int32, torch.int64, torch.bool]:
            self.assertRaises(RuntimeError, lambda: torch._foreach_add_(tensors, float_scalar))
        else:
            torch._foreach_add_(tensors, float_scalar)
            self.assertEqual(res, tensors)

    @dtypes(*torch.testing.get_all_dtypes())
    def test_complex_scalar(self, device, dtype):
        tensors = [torch.zeros(10, 10, device=device, dtype=dtype) for _ in range(10)]
        complex_scalar = 3 + 5j

        # bool tensor + 1 will result in int64 tensor
        expected = [torch.add(complex_scalar, torch.zeros(10, 10, device=device, dtype=dtype)) for _ in range(10)]

        if dtype in [torch.float16, torch.float32, torch.float64, torch.bfloat16] and device == 'cuda:0':
            # value cannot be converted to dtype without overflow: 
            self.assertRaises(RuntimeError, lambda: torch._foreach_add_(tensors, complex_scalar))
            self.assertRaises(RuntimeError, lambda: torch._foreach_add(tensors, complex_scalar))
            return

        res = torch._foreach_add(tensors, complex_scalar)
        self.assertEqual(res, expected)

        if dtype not in [torch.complex64, torch.complex128]:
            self.assertRaises(RuntimeError, lambda: torch._foreach_add_(tensors, complex_scalar))
        else:
            torch._foreach_add_(tensors, complex_scalar)
            self.assertEqual(res, tensors)

    @dtypes(*torch.testing.get_all_dtypes())
    def test_bool_scalar(self, device, dtype):
        tensors = [torch.zeros(10, 10, device=device, dtype=dtype) for _ in range(10)]
        bool_scalar = True

        expected = [torch.ones(10, 10, device=device, dtype=dtype) for _ in range(10)]

        res = torch._foreach_add(tensors, bool_scalar)
        self.assertEqual(res, expected)

        torch._foreach_add_(tensors, bool_scalar)
        self.assertEqual(res, tensors)

    @dtypes(*torch.testing.get_all_dtypes())
    def test_add_with_different_size_tensors(self, device, dtype):
        if dtype == torch.bool: 
            return
        tensors = [torch.zeros(10 + n, 10 + n, device=device, dtype=dtype) for n in range(10)]
        expected = [torch.ones(10 + n, 10 + n, device=device, dtype=dtype) for n in range(10)]

        torch._foreach_add_(tensors, 1)
        self.assertEqual(expected, tensors)

    @dtypes(*torch.testing.get_all_dtypes())
    def test_add_scalar_with_empty_list_and_empty_tensor(self, device, dtype):
        # TODO: enable empty list case
        for tensors in [[torch.randn([0])]]:
            res = torch._foreach_add(tensors, 1)
            self.assertEqual(res, tensors)

            torch._foreach_add_(tensors, 1)
            self.assertEqual(res, tensors)

    @dtypes(*torch.testing.get_all_dtypes())
    def test_add_scalar_with_overlapping_tensors(self, device, dtype):
        tensors = [torch.ones(1, 1, device=device, dtype=dtype).expand(2, 1, 3)]
        expected = [torch.tensor([[[2, 2, 2]], [[2, 2, 2]]], dtype=dtype, device=device)]

        # bool tensor + 1 will result in int64 tensor
        if dtype == torch.bool: 
            expected[0] = expected[0].to(torch.int64).add(1)

        res = torch._foreach_add(tensors, 1)
        self.assertEqual(res, expected)

    def test_bin_op_scalar_with_different_tensor_dtypes(self, device):
        tensors = [torch.tensor([1.1], dtype=torch.float, device=device), 
                   torch.tensor([1], dtype=torch.long, device=device)]

        for bin_op in self.bin_ops: 
            self.assertRaises(RuntimeError, lambda: bin_op(tensors, 1))

    #
    # Ops with list
    #
    @dtypes(*torch.testing.get_all_dtypes())
    def test_bin_op_list(self, device, dtype):
        if dtype == torch.bool:
            return

        tensors1 = [torch.zeros(20, 20, device=device, dtype=dtype) for _ in range(20)]
        tensors2 = [torch.ones(20, 20, device=device, dtype=dtype) for _ in range(20)]

        # add
        res = torch._foreach_add(tensors1, tensors2)
        torch._foreach_add_(tensors1, tensors2)
        self.assertEqual(res, tensors1)
        self.assertEqual(tensors1, [torch.ones(20, 20, device=device, dtype=dtype) for _ in range(20)])

        res = torch._foreach_add(tensors1, tensors2, 2)
        torch._foreach_add_(tensors1, tensors2, 2)
        self.assertEqual(res, tensors1)
        self.assertEqual(tensors1, [torch.ones(20, 20, device=device, dtype=dtype).mul(3) for _ in range(20)])

        # sub
        res = torch._foreach_sub(tensors1, tensors2, 3)
        torch._foreach_sub_(tensors1, tensors2, 3)
        self.assertEqual(res, tensors1)
        self.assertEqual(tensors1, [torch.zeros(20, 20, device=device, dtype=dtype) for _ in range(20)])

        # mul
        res = torch._foreach_mul(tensors1, tensors2)
        torch._foreach_mul_(tensors1, tensors2)
        self.assertEqual(res, tensors1)
        self.assertEqual(tensors1, [torch.zeros(20, 20, device=device, dtype=dtype) for _ in range(20)])

        # div
        torch._foreach_add_(tensors1, 4)
        torch._foreach_add_(tensors2, 1)
        if device != 'cuda:0' and dtype in [torch.int8, torch.int16, torch.int32, torch.int64, torch.uint8]:
            # Integer division of tensors using div or / is no longer supported
            self.assertRaises(RuntimeError, lambda: torch._foreach_div(tensors1, tensors2))
            self.assertRaises(RuntimeError, lambda: torch._foreach_div_(tensors1, tensors2))
            return

        res = torch._foreach_div(tensors1, tensors2)
        torch._foreach_div_(tensors1, tensors2)
        self.assertEqual(res, tensors1)
        self.assertEqual(tensors1, [torch.ones(20, 20, device=device, dtype=dtype).mul(2) for _ in range(20)])

    def test_bin_op_list_error_cases(self, device):
        tensors1 = []
        tensors2 = []

        for bin_op in self.bin_ops: 
            # Empty lists
            with self.assertRaises(RuntimeError):
                bin_op(tensors1, tensors2)

            # One empty list
            tensors1.append(torch.tensor([1], device=device))
            with self.assertRaises(RuntimeError):
                bin_op(tensors1, tensors2)

            # Lists have different amount of tensors
            tensors2.append(torch.tensor([1], device=device))
            tensors2.append(torch.tensor([1], device=device))
            with self.assertRaises(RuntimeError):
                bin_op(tensors1, tensors2)

            # Different dtypes
            tensors1 = [torch.zeros(2, 2, device=device, dtype=torch.float) for _ in range(2)]
            tensors2 = [torch.ones(2, 2, device=device, dtype=torch.int) for _ in range(2)]

            with self.assertRaises(RuntimeError):
                bin_op(tensors1, tensors2)

instantiate_device_type_tests(TestForeach, globals())

if __name__ == '__main__':
    run_tests()
